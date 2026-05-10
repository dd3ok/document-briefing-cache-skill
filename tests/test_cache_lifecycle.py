from document_briefing_cache.cache import JsonFileCache
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
