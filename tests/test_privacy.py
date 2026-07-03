import json

import pytest

from document_briefing_cache.models import CacheConfig, DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline
from document_briefing_cache.privacy import redact_document_input, redact_pii_text, redact_secret_text
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


class CapturingSummarizer(RuleBasedExtractiveSummarizer):
    summarizer_id = "capturing-redaction-v1"

    def __init__(self):
        self.seen_document_text = ""
        self.seen_sections = []

    def summarize(self, document, sections, content_fingerprint):
        self.seen_document_text = document.text or ""
        self.seen_sections = [section.text for section in sections]
        return super().summarize(document, sections, content_fingerprint)


def test_pipeline_redacts_pii_from_output_and_cached_summaries(tmp_path):
    docs = [
        DocumentInput(
            document_id="privacy",
            title="Customer follow-up",
            text="Action: Support should email alice@example.com and call 010-1234-5678 by 2026-05-12.",
        )
    ]
    config = CacheConfig(cache_dir=str(tmp_path), output_cache=True, redact_pii=True)

    result = BriefingPipeline(cache_config=config).run(docs, use_output_cache=True)

    assert "alice@example.com" not in result.output
    assert "010-1234-5678" not in result.output
    assert "REDACTED:email" in result.output
    assert "REDACTED:phone" in result.output
    assert result.stats.pii_redactions >= 2

    cached_text = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert "alice@example.com" not in cached_text
    assert "010-1234-5678" not in cached_text


def test_pipeline_hmac_signs_cache_entries_from_configured_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DBC_TEST_HMAC", "secret")
    docs = [DocumentInput(document_id="signed", title="Signed", text="Decision: proceed.")]
    config = CacheConfig(cache_dir=str(tmp_path), cache_hmac_secret_env="DBC_TEST_HMAC")

    BriefingPipeline(cache_config=config).run(docs)

    cache_file = next((tmp_path / "document_summaries").glob("*.json"))
    envelope = json.loads(cache_file.read_text(encoding="utf-8"))
    assert envelope["payload_hmac_sha256"]


def test_redacted_run_does_not_use_prior_unredacted_output_cache(tmp_path):
    docs = [
        DocumentInput(
            document_id="ticket-privacy",
            title="Customer follow-up",
            text="Action: Support should email alice@example.com by 2026-05-12.",
        )
    ]

    raw_result = BriefingPipeline(cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=True)).run(docs, use_output_cache=True)
    assert "alice@example.com" in raw_result.output

    redacted_config = CacheConfig(cache_dir=str(tmp_path), output_cache=True, redact_pii=True)
    redacted_result = BriefingPipeline(cache_config=redacted_config).run(docs, use_output_cache=True)

    assert redacted_result.stats.output_cache_hit is False
    assert redacted_result.stats.document_cache_hits == 0
    assert "alice@example.com" not in redacted_result.output
    assert "REDACTED:email" in redacted_result.output


def test_redacted_run_does_not_use_prior_unredacted_document_cache(tmp_path):
    docs = [
        DocumentInput(
            document_id="ticket-privacy",
            title="Customer follow-up",
            text="Action: Support should email alice@example.com by 2026-05-12.",
        )
    ]

    BriefingPipeline(cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=False)).run(docs, use_output_cache=False)

    redacted_config = CacheConfig(cache_dir=str(tmp_path), output_cache=False, redact_pii=True)
    redacted_result = BriefingPipeline(cache_config=redacted_config).run(docs, use_output_cache=False)

    assert redacted_result.stats.document_cache_hits == 0
    assert redacted_result.stats.document_cache_misses == 1
    assert "alice@example.com" not in redacted_result.output
    assert "REDACTED:email" in redacted_result.output


def test_redaction_runs_before_summarizer_sees_document_text(tmp_path):
    docs = [
        DocumentInput(
            document_id="ticket-privacy",
            title="Customer follow-up",
            text="Action: Support should email alice@example.com and call 010-1234-5678 by 2026-05-12.",
        )
    ]
    summarizer = CapturingSummarizer()

    BriefingPipeline(
        cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=False, redact_pii=True),
        summarizer=summarizer,
    ).run(docs, use_output_cache=False)

    seen_text = "\n".join([summarizer.seen_document_text, *summarizer.seen_sections])
    assert "alice@example.com" not in seen_text
    assert "010-1234-5678" not in seen_text
    assert "[REDACTED:email]" in seen_text
    assert "[REDACTED:phone]" in seen_text


def test_redacted_document_identity_does_not_break_cache_hits(tmp_path):
    docs = [
        DocumentInput(
            document_id="alice@example.com",
            source="mailto:alice@example.com",
            title="Customer follow-up",
            text="Action: Support should call 010-1234-5678 by 2026-05-12.",
        )
    ]
    config = CacheConfig(cache_dir=str(tmp_path), output_cache=False, redact_pii=True)

    first = BriefingPipeline(cache_config=config).run(docs, use_output_cache=False)
    second = BriefingPipeline(cache_config=config).run(docs, use_output_cache=False)

    assert second.stats.document_cache_hits == 1
    visible_stats = json.dumps(first.stats.model_dump(mode="json"), ensure_ascii=False)
    assert "alice@example.com" not in visible_stats
    assert "mailto:alice@example.com" not in visible_stats
    cached_text = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert "alice@example.com" not in cached_text
    assert "010-1234-5678" not in cached_text


def test_redacted_cache_keys_do_not_alias_different_raw_contacts(tmp_path):
    docs = [
        DocumentInput(document_id="same-ticket", title="A", text="Action: Support should email alice@example.com by 2026-05-12."),
        DocumentInput(document_id="same-ticket", title="A", text="Action: Support should email bob@example.com by 2026-05-12."),
    ]
    config = CacheConfig(cache_dir=str(tmp_path), output_cache=False, redact_pii=True)

    result = BriefingPipeline(cache_config=config).run(docs, use_output_cache=False)

    assert result.stats.document_cache_misses == 2
    assert len(list((tmp_path / "document_summaries").glob("*.json"))) == 2


def test_redact_document_input_recurses_raw_and_metadata_without_mutating_original():
    document = DocumentInput(
        document_id="alice@example.com",
        source="mailto:alice@example.com",
        title="Customer follow-up",
        text="Action: email alice@example.com by 2026-05-12.",
        raw={"contact": {"email": "alice@example.com", "phone": "010-1234-5678"}},
        metadata={"requester": "alice@example.com"},
    )

    redacted, count = redact_document_input(document)

    assert count >= 5
    assert redacted.document_id is None
    assert redacted.source is None
    redacted_payload = json.dumps(redacted.model_dump(mode="json"), ensure_ascii=False)
    assert "alice@example.com" not in redacted_payload
    assert "010-1234-5678" not in redacted_payload
    original_payload = json.dumps(document.model_dump(mode="json"), ensure_ascii=False)
    assert "alice@example.com" in original_payload


def test_pii_redaction_preserves_non_pii_protected_values():
    text = "Email bob@example.com, call +1 415-555-1212, keep INC-2026-091, 2026-05-12, 2.4%, and 183 ms."

    redacted, count = redact_pii_text(text)

    assert count == 2
    assert "bob@example.com" not in redacted
    assert "+1 415-555-1212" not in redacted
    assert "INC-2026-091" in redacted
    assert "2026-05-12" in redacted
    assert "2.4%" in redacted
    assert "183 ms" in redacted


def test_secret_redaction_covers_common_tokens_and_preserves_operational_values():
    text = (
        "Action: Rotate api_key=sk_test_123456789abcdef and Authorization: Bearer abcdef1234567890. "
        "Webhook https://hooks.slack.com/services/T000/B000/SECRET123456 should be replaced. "
        "Card 4111-1111-1111-1111 was pasted by mistake. "
        "Keep INC-2026-091, 2026-05-12, 2.4%, and 183 ms."
    )

    redacted, count = redact_secret_text(text)

    assert count == 4
    assert "sk_test_123456789abcdef" not in redacted
    assert "abcdef1234567890" not in redacted
    assert "hooks.slack.com/services" not in redacted
    assert "4111-1111-1111-1111" not in redacted
    assert "[REDACTED:secret]" in redacted
    assert "[REDACTED:webhook-url]" in redacted
    assert "[REDACTED:card]" in redacted
    assert "INC-2026-091" in redacted
    assert "2026-05-12" in redacted
    assert "2.4%" in redacted
    assert "183 ms" in redacted


def test_secret_redaction_covers_quoted_assignment_keys():
    text = (
        '{"api_key": "sk_test_123456789abcdef", '
        "'client_secret': 'client-secret-123456789', "
        '"owner": "ops"}'
    )

    redacted, count = redact_secret_text(text)

    assert count == 2
    assert "sk_test_123456789abcdef" not in redacted
    assert "client-secret-123456789" not in redacted
    assert '"api_key": "[REDACTED:secret]"' in redacted
    assert "'client_secret': '[REDACTED:secret]'" in redacted
    assert '"owner": "ops"' in redacted


def test_pipeline_redacts_secrets_before_summarizer_output_and_cache(tmp_path):
    secret = "sk_test_123456789abcdef"
    docs = [
        DocumentInput(
            document_id="secret-ticket",
            title="Secret cleanup",
            text=f"Action: Security should rotate api_key={secret} and Authorization: Bearer abcdef1234567890.",
        )
    ]
    summarizer = CapturingSummarizer()

    result = BriefingPipeline(
        cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=False, redact_secrets=True),
        summarizer=summarizer,
    ).run(docs, use_output_cache=False)

    seen_text = "\n".join([summarizer.seen_document_text, *summarizer.seen_sections, result.output])
    assert secret not in seen_text
    assert "abcdef1234567890" not in seen_text
    assert "[REDACTED:secret]" in seen_text
    assert result.stats.secret_redactions == 2
    assert result.stats.pii_redactions == 0

    cached_text = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert secret not in cached_text
    assert "abcdef1234567890" not in cached_text


def test_secret_redacted_run_does_not_use_prior_unredacted_cache(tmp_path):
    secret = "sk_test_123456789abcdef"
    docs = [DocumentInput(document_id="secret-ticket", title="Secret cleanup", text=f"Action: Rotate api_key={secret}.")]

    raw_result = BriefingPipeline(cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=True)).run(docs, use_output_cache=True)
    assert secret.replace("_", "\\_") in raw_result.output

    redacted_result = BriefingPipeline(
        cache_config=CacheConfig(cache_dir=str(tmp_path), output_cache=True, redact_secrets=True)
    ).run(docs, use_output_cache=True)

    assert redacted_result.stats.output_cache_hit is False
    assert redacted_result.stats.document_cache_hits == 0
    assert secret not in redacted_result.output
    assert "REDACTED:secret" in redacted_result.output


def test_pipeline_hmac_secret_env_missing_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("DBC_MISSING_HMAC", raising=False)

    with pytest.raises(RuntimeError, match="DBC_MISSING_HMAC"):
        BriefingPipeline(cache_config=CacheConfig(cache_dir=str(tmp_path), cache_hmac_secret_env="DBC_MISSING_HMAC"))
