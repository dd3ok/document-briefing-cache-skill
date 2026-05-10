from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


class CountingSummarizer(RuleBasedExtractiveSummarizer):
    summarizer_id = "counting-rules-v1"

    def __init__(self):
        self.calls = 0

    def summarize(self, document, sections, content_fingerprint):
        self.calls += 1
        return super().summarize(document, sections, content_fingerprint)


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
