from document_briefing_cache.cache import JsonFileCache
from document_briefing_cache.hashing import document_content_fingerprint, document_summary_cache_key
from document_briefing_cache.models import DocumentInput, DocumentSummaryState, KeyPoint
from document_briefing_cache.pipeline import BriefingPipeline, SKILL_VERSION
from document_briefing_cache.summarizers import BaseSummarizer, RuleBasedExtractiveSummarizer


class CountingSummarizer(RuleBasedExtractiveSummarizer):
    summarizer_id = "counting-rules-v1"

    def __init__(self):
        self.calls = 0

    def summarize(self, document, sections, content_fingerprint):
        self.calls += 1
        return super().summarize(document, sections, content_fingerprint)


class MissingEvidenceSummarizer(BaseSummarizer):
    summarizer_id = "missing-evidence-v1"

    def summarize(self, document, sections, content_fingerprint):
        return DocumentSummaryState(
            document_id=document.document_id or content_fingerprint[:16],
            content_fingerprint=content_fingerprint,
            summary="Unsupported item.",
            key_points=[KeyPoint(text="Unsupported item.")],
            summarizer_id=self.summarizer_id,
        )


def sample_docs():
    return [
        DocumentInput(document_id="m1", title="Meeting", text="Decision: approved launch. Action: Data team should validate by 2026-05-10. Owner: Data team."),
        DocumentInput(document_id="l1", title="Incident", text="Payment API error rate reached 2.4%. Risk: conversion may drop. Action: Backend should inspect deployment diff."),
    ]


def test_document_level_cache_reuses_summaries(tmp_path):
    summarizer1 = CountingSummarizer()
    pipeline1 = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer1)
    first = pipeline1.run(sample_docs(), mode="brief", use_output_cache=False)
    assert first.stats.document_cache_misses == 2
    assert first.stats.summarizer_calls == 2
    assert summarizer1.calls == 2

    summarizer2 = CountingSummarizer()
    pipeline2 = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer2)
    second = pipeline2.run(sample_docs(), mode="digest", use_output_cache=False)
    assert second.stats.document_cache_hits == 2
    assert second.stats.summarizer_calls == 0
    assert summarizer2.calls == 0


def test_output_cache_reuses_final_string(tmp_path):
    summarizer1 = CountingSummarizer()
    pipeline1 = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer1)
    first = pipeline1.run(sample_docs(), mode="brief", use_output_cache=True)
    assert first.stats.output_cache_hit is False
    assert first.stats.summarizer_calls == 2

    summarizer2 = CountingSummarizer()
    pipeline2 = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer2)
    second = pipeline2.run(sample_docs(), mode="brief", use_output_cache=True)
    assert second.stats.output_cache_hit is True
    assert second.stats.summarizer_calls == 0
    assert second.summaries == []
    assert first.output == second.output


def test_adding_one_document_summarizes_only_new_document(tmp_path):
    pipeline1 = BriefingPipeline(cache_dir=tmp_path, summarizer=CountingSummarizer())
    pipeline1.run(sample_docs(), mode="brief", use_output_cache=False)

    docs = sample_docs() + [DocumentInput(document_id="p1", title="Policy", text="Policy: receipts must be submitted within 14 days.")]
    summarizer2 = CountingSummarizer()
    pipeline2 = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer2)
    result = pipeline2.run(docs, mode="brief", use_output_cache=False)
    assert result.stats.document_cache_hits == 2
    assert result.stats.document_cache_misses == 1
    assert result.stats.summarizer_calls == 1


def test_pipeline_copies_normalization_unknowns_to_summary_unknowns(tmp_path):
    docs = [
        DocumentInput(
            document_id="opaque",
            title="Opaque",
            text="Some fallback text.",
            metadata={"normalization_unknowns": ["Unsupported payload type: object"]},
        )
    ]

    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="debug", use_output_cache=False)

    assert "Unsupported payload type: object" in result.summaries[0].unknowns


def test_cached_summary_preserves_normalization_unknowns(tmp_path):
    base_doc = DocumentInput(document_id="opaque", title="Opaque", text="Some fallback text.")
    pipeline1 = BriefingPipeline(cache_dir=tmp_path)
    pipeline1.run([base_doc], mode="debug", use_output_cache=False)

    doc_with_unknowns = DocumentInput(
        document_id="opaque",
        title="Opaque",
        text="Some fallback text.",
        metadata={"normalization_unknowns": ["Unsupported payload type: object"]},
    )
    result = BriefingPipeline(cache_dir=tmp_path).run([doc_with_unknowns], mode="debug", use_output_cache=False)

    assert result.stats.document_cache_hits == 1
    assert "Unsupported payload type: object" in result.summaries[0].unknowns


def test_normalization_unknowns_do_not_leak_from_document_cache(tmp_path):
    unknown_doc = DocumentInput(
        document_id="opaque",
        title="Opaque",
        text="Some fallback text.",
        metadata={"normalization_unknowns": ["Unsupported payload type: object"]},
    )
    first = BriefingPipeline(cache_dir=tmp_path).run([unknown_doc], mode="debug", use_output_cache=False)
    assert first.stats.document_cache_misses == 1
    assert "Unsupported payload type: object" in first.summaries[0].unknowns

    normal_doc = DocumentInput(document_id="opaque", title="Opaque", text="Some fallback text.")
    result = BriefingPipeline(cache_dir=tmp_path).run([normal_doc], mode="debug", use_output_cache=False)

    assert result.stats.document_cache_hits == 1
    assert result.stats.summarizer_calls == 0
    assert "Unsupported payload type: object" not in result.summaries[0].unknowns
    assert "Unsupported payload type: object" not in result.output


def test_output_cache_does_not_hide_normalization_unknowns(tmp_path):
    base_doc = DocumentInput(document_id="opaque", title="Opaque", text="Some fallback text.")
    pipeline1 = BriefingPipeline(cache_dir=tmp_path)
    first = pipeline1.run([base_doc], mode="debug", use_output_cache=True)
    assert first.stats.output_cache_hit is False

    doc_with_unknowns = DocumentInput(
        document_id="opaque",
        title="Opaque",
        text="Some fallback text.",
        metadata={"normalization_unknowns": ["Unsupported payload type: object"]},
    )
    result = BriefingPipeline(cache_dir=tmp_path).run([doc_with_unknowns], mode="debug", use_output_cache=True)

    assert result.stats.output_cache_hit is False
    assert "Unsupported payload type: object" in result.output


def test_validation_errors_prevent_document_cache_write(tmp_path):
    docs = [DocumentInput(document_id="bad", title="Bad", text="Source text.")]
    pipeline = BriefingPipeline(cache_dir=tmp_path, summarizer=MissingEvidenceSummarizer())

    result = pipeline.run(docs, use_output_cache=False)

    assert result.stats.evidence_validation_errors > 0
    assert list((tmp_path / "document_summaries").glob("*.json")) == []


def test_empty_document_summary_does_not_require_impossible_summary_evidence(tmp_path):
    docs = [DocumentInput(document_id="empty", title="Empty doc", text="")]
    summarizer1 = CountingSummarizer()
    first = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer1).run(docs, use_output_cache=False)

    assert first.stats.evidence_validation_errors == 0
    assert first.stats.document_cache_misses == 1
    assert first.stats.summarizer_calls == 1
    assert "Document text is empty after normalization." in first.summaries[0].unknowns

    summarizer2 = CountingSummarizer()
    second = BriefingPipeline(cache_dir=tmp_path, summarizer=summarizer2).run(docs, use_output_cache=False)

    assert second.stats.document_cache_hits == 1
    assert second.stats.summarizer_calls == 0
    assert summarizer2.calls == 0


def test_empty_document_title_with_protected_values_does_not_fail_evidence_validation(tmp_path):
    docs = [DocumentInput(document_id="empty-budget", title="Budget 2026 Plan", text="")]

    result = BriefingPipeline(cache_dir=tmp_path, summarizer=CountingSummarizer()).run(docs, use_output_cache=False)

    assert result.stats.evidence_validation_errors == 0
    assert result.stats.document_cache_misses == 1
    assert "Document text is empty after normalization." in result.summaries[0].unknowns
    assert list((tmp_path / "document_summaries").glob("*.json"))


def test_old_skill_version_cached_summary_missing_evidence_is_cache_miss(tmp_path):
    doc = DocumentInput(document_id="stale", title="Stale", text="Decision: proceed.")
    fingerprint = document_content_fingerprint(doc)
    old_key = document_summary_cache_key(
        doc,
        fingerprint=fingerprint,
        summarizer_id=CountingSummarizer.summarizer_id,
        skill_version="0.3.0",
        redaction_policy_id="none",
    )
    old_summary = DocumentSummaryState(
        document_id=doc.document_id,
        content_fingerprint=fingerprint,
        summary="Decision: proceed.",
        key_points=[KeyPoint(text="Decision: proceed.")],
        summarizer_id=CountingSummarizer.summarizer_id,
    )
    pipeline = BriefingPipeline(cache_dir=tmp_path, summarizer=CountingSummarizer())
    pipeline.document_cache.set_model(old_key, old_summary)

    result = pipeline.run([doc], use_output_cache=False)

    assert result.stats.document_cache_hits == 0
    assert result.stats.document_cache_misses == 1
    assert result.stats.summarizer_calls == 1


def test_schema_100_cached_summary_is_treated_as_miss_after_v11(tmp_path):
    docs = [DocumentInput(document_id="schema", title="Schema", text="Decision: proceed.")]
    fingerprint = document_content_fingerprint(docs[0])
    key = document_summary_cache_key(
        docs[0],
        fingerprint=fingerprint,
        summarizer_id="counting-rules-v1",
        skill_version=SKILL_VERSION,
        schema_version="1.0.0",
    )
    old_summary = DocumentSummaryState(
        schema_version="1.0.0",
        document_id="schema",
        content_fingerprint=fingerprint,
        summary="Old schema.",
        summarizer_id="counting-rules-v1",
    )
    JsonFileCache(tmp_path, "document_summaries").set_model(key, old_summary)

    result = BriefingPipeline(cache_dir=tmp_path, summarizer=CountingSummarizer()).run(docs, use_output_cache=False)

    assert result.stats.document_cache_hits == 0
    assert result.stats.document_cache_misses == 1
    assert result.stats.summarizer_calls == 1


def test_corrupt_document_cache_event_uses_validation_failed_reason(tmp_path):
    doc = DocumentInput(document_id="corrupt-doc", title="Corrupt", text="Action: owner should inspect cache.")
    pipeline = BriefingPipeline(cache_dir=tmp_path)
    first = pipeline.run([doc], use_output_cache=False)
    key = first.stats.cache_keys[next(name for name in first.stats.cache_keys if name.startswith("document:"))]
    path = pipeline.document_cache.path_for(key)
    path.write_text("{not-json", encoding="utf-8")

    result = BriefingPipeline(cache_dir=tmp_path).run([doc], use_output_cache=False)

    assert result.stats.document_cache_corrupt == 1
    assert result.stats.document_cache_events[0].status == "corrupt"
    assert result.stats.document_cache_events[0].reason == "corrupt_validation_failed"
