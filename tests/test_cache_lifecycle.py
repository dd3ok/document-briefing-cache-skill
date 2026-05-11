import json
import os
import hashlib
import tempfile
from pathlib import Path

import pytest

from document_briefing_cache.cache import JsonFileCache
from document_briefing_cache.hashing import document_content_fingerprint, document_summary_cache_key
from document_briefing_cache.models import CacheConfig, DocumentInput, DocumentSummaryState, EvidenceRef, Metric
from document_briefing_cache.pipeline import BriefingPipeline
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


class CountingSummarizer(RuleBasedExtractiveSummarizer):
    summarizer_id = "counting-cache-lifecycle-v1"

    def __init__(self):
        self.calls = 0

    def summarize(self, document, sections, content_fingerprint):
        self.calls += 1
        return super().summarize(document, sections, content_fingerprint)


class InvalidSummarySummarizer(RuleBasedExtractiveSummarizer):
    summarizer_id = "invalid-summary-v1"

    def summarize(self, document, sections, content_fingerprint):
        return DocumentSummaryState(
            document_id=document.document_id or "doc",
            content_fingerprint=content_fingerprint,
            summary="Error rate reached 2.5%.",
            metrics=[
                Metric(
                    value="2.5",
                    unit="%",
                    evidence=[EvidenceRef(document_id=document.document_id or "doc", section_id="s1", quote="Error rate reached 2.5%.")],
                )
            ],
            summarizer_id=self.summarizer_id,
        )


def test_json_cache_expires_entries_and_reports_prune(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries")
    cache.set_json("expired", {"value": 1}, ttl_seconds=-1)

    assert cache.get_json_with_status("expired").status == "expired"

    result = cache.prune()

    assert result.entries_deleted == 1
    assert cache.get_json_with_status("expired").status == "miss"


def test_pipeline_treats_expired_document_summary_as_miss(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Action: Backend should patch by 2026-05-07.")]
    config = CacheConfig(cache_dir=str(tmp_path), document_ttl_seconds=-1, output_cache=False)

    first_summarizer = CountingSummarizer()
    BriefingPipeline(cache_config=config, summarizer=first_summarizer).run(docs)
    assert first_summarizer.calls == 1

    second_summarizer = CountingSummarizer()
    result = BriefingPipeline(cache_config=config, summarizer=second_summarizer).run(docs)

    assert second_summarizer.calls == 1
    assert result.stats.document_cache_expired == 1
    assert result.stats.document_cache_misses == 1


def test_ephemeral_policy_deletes_entries_created_during_run(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Decision: proceed.")]
    config = CacheConfig(cache_dir=str(tmp_path), policy="ephemeral", output_cache=True)

    result = BriefingPipeline(cache_config=config).run(docs, use_output_cache=True)

    assert result.stats.delete_on_exit_applied is True
    assert list(tmp_path.rglob("*.json")) == []


def test_invalid_summary_is_not_written_to_output_cache(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Error rate reached 2.4%.")]
    config = CacheConfig(cache_dir=str(tmp_path), output_cache=True)

    result = BriefingPipeline(cache_config=config, summarizer=InvalidSummarySummarizer()).run(docs)

    assert result.stats.evidence_validation_errors > 0
    assert list((tmp_path / "rendered_outputs").glob("*.json")) == []


def test_read_only_policy_does_not_touch_cache_file_on_hit(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Decision: proceed.")]
    write_config = CacheConfig(cache_dir=str(tmp_path), output_cache=False, document_ttl_seconds=None)
    BriefingPipeline(cache_config=write_config).run(docs)
    cache_file = next((tmp_path / "document_summaries").glob("*.json"))
    before = cache_file.read_text(encoding="utf-8")

    read_config = CacheConfig(cache_dir=str(tmp_path), policy="read_only", output_cache=False)
    result = BriefingPipeline(cache_config=read_config).run(docs)

    assert result.stats.document_cache_hits == 1
    assert cache_file.read_text(encoding="utf-8") == before


def test_cache_clear_removes_namespace(tmp_path):
    cache = JsonFileCache(tmp_path, "rendered_outputs")
    cache.set_text("out", "hello")

    result = cache.clear()

    assert result.entries_deleted == 1
    assert cache.get_text_with_status("out").status == "miss"


def test_json_cache_uses_private_directory_and_file_permissions():
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache = JsonFileCache(tmp_path, "document_summaries")
        cache.set_json("private", {"value": 1})

        cache_file = cache.path_for("private")

        if os.name == "posix":
            if (cache.root.stat().st_mode & 0o777) != 0o700:
                pytest.skip("filesystem does not honor POSIX chmod")
            assert (cache_file.stat().st_mode & 0o777) == 0o600


def test_json_cache_rejects_envelope_key_namespace_and_digest_mismatch(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries")
    cache.set_json("safe", {"value": 1})
    path = cache.path_for("safe")
    envelope = json.loads(path.read_text(encoding="utf-8"))

    envelope["key"] = "other"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    assert cache.get_json_with_status("safe").status == "corrupt"

    cache.set_json("safe", {"value": 1})
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["value"] = 2
    path.write_text(json.dumps(envelope), encoding="utf-8")
    assert cache.get_json_with_status("safe").status == "corrupt"


def test_json_cache_hmac_rejects_tampering_even_when_digest_is_updated(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    cache.set_json("safe", {"value": 1})
    path = cache.path_for("safe")
    envelope = json.loads(path.read_text(encoding="utf-8"))

    envelope["payload"]["value"] = 2
    envelope["payload_sha256"] = hashlib.sha256(
        json.dumps(envelope["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    path.write_text(json.dumps(envelope), encoding="utf-8")

    assert cache.get_json_with_status("safe").status == "corrupt"


def test_json_cache_requires_payload_digest_for_v1_envelopes(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries")
    cache.set_json("missing-digest", {"value": 1})
    path = cache.path_for("missing-digest")
    envelope = json.loads(path.read_text(encoding="utf-8"))

    envelope.pop("payload_sha256")
    path.write_text(json.dumps(envelope), encoding="utf-8")

    assert cache.get_json_with_status("missing-digest").status == "corrupt"


def test_json_cache_prune_removes_v1_envelopes_missing_payload_digest(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries")
    cache.set_json("missing-digest", {"value": 1})
    path = cache.path_for("missing-digest")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope.pop("payload_sha256")
    path.write_text(json.dumps(envelope), encoding="utf-8")

    result = cache.prune()

    assert result.entries_deleted == 1
    assert cache.get_json_with_status("missing-digest").status == "miss"


def test_json_cache_hmac_requires_signed_entries(tmp_path):
    unsigned_cache = JsonFileCache(tmp_path, "document_summaries")
    unsigned_cache.set_json("legacy", {"value": 1})

    signed_cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")

    assert signed_cache.get_json_with_status("legacy").status == "corrupt"


def test_json_cache_hmac_signed_entry_fails_closed_without_secret(tmp_path):
    signed_cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    signed_cache.set_json("signed", {"value": 1})

    unsigned_reader = JsonFileCache(tmp_path, "document_summaries")

    assert unsigned_reader.get_json_with_status("signed").status == "corrupt"


def test_json_cache_hmac_rejects_wrong_secret(tmp_path):
    signed_cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret-a")
    signed_cache.set_json("signed", {"value": 1})

    wrong_secret_reader = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret-b")

    assert wrong_secret_reader.get_json_with_status("signed").status == "corrupt"


def test_json_cache_hmac_rejects_expires_at_tampering(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    cache.set_json("signed-expiry", {"value": 1}, ttl_seconds=-1)
    path = cache.path_for("signed-expiry")
    envelope = json.loads(path.read_text(encoding="utf-8"))

    envelope["expires_at"] = None
    path.write_text(json.dumps(envelope), encoding="utf-8")

    assert cache.get_json_with_status("signed-expiry").status == "corrupt"


def test_json_cache_hmac_rejects_cache_version_tampering(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    cache.set_json("signed-version", {"value": 1})
    path = cache.path_for("signed-version")
    envelope = json.loads(path.read_text(encoding="utf-8"))

    envelope["cache_version"] = "0.9"
    path.write_text(json.dumps(envelope), encoding="utf-8")

    assert cache.get_json_with_status("signed-version").status == "corrupt"


def test_json_cache_signed_entry_survives_last_accessed_updates(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    cache.set_json("signed", {"value": 1})

    assert cache.get_json_with_status("signed").status == "hit"
    assert cache.get_json_with_status("signed").status == "hit"


def test_json_cache_prune_skips_signed_entries_without_secret(tmp_path):
    signed_cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    signed_cache.set_json("signed", {"value": 1}, ttl_seconds=3600)

    unsigned_reader = JsonFileCache(tmp_path, "document_summaries")
    result = unsigned_reader.prune()

    assert result.entries_deleted == 0
    assert signed_cache.get_json_with_status("signed").status == "hit"


def test_json_cache_prune_removes_invalid_signed_envelopes(tmp_path):
    cache = JsonFileCache(tmp_path, "document_summaries", hmac_secret="secret")
    cache.set_json("signed-expiry", {"value": 1}, ttl_seconds=3600)
    path = cache.path_for("signed-expiry")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["expires_at"] = None
    path.write_text(json.dumps(envelope), encoding="utf-8")

    result = cache.prune()

    assert result.entries_deleted == 1
    assert cache.get_json_with_status("signed-expiry").status == "miss"


def test_json_cache_hashes_unsafe_keys_without_collision(tmp_path):
    cache = JsonFileCache(tmp_path, "rendered_outputs")

    left = cache.path_for("a/b")
    right = cache.path_for("ab")

    assert left.name.startswith("sha256-")
    assert left != right


def test_pipeline_ignores_cached_summary_with_wrong_contract(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Decision: proceed.")]
    config = CacheConfig(cache_dir=str(tmp_path), output_cache=False)
    summarizer = CountingSummarizer()
    pipeline = BriefingPipeline(cache_config=config, summarizer=summarizer)
    real_fingerprint = document_content_fingerprint(docs[0])

    fingerprint = "not-the-real-fingerprint"
    bad_summary = DocumentSummaryState(
        document_id="x",
        content_fingerprint=fingerprint,
        summary="Tampered cached summary.",
        summarizer_id="wrong-summarizer",
    )
    summary_key = document_summary_cache_key(
        docs[0],
        fingerprint=real_fingerprint,
        summarizer_id=summarizer.summarizer_id,
        skill_version=pipeline.skill_version,
    )
    pipeline.document_cache.set_model(summary_key, bad_summary)

    result = BriefingPipeline(cache_config=config, summarizer=summarizer).run(docs)

    assert summarizer.calls == 1
    assert result.stats.document_cache_corrupt == 1
    assert "Tampered cached summary" not in result.output
