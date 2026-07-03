from document_briefing_cache.models import CacheConfig, DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


def test_pipeline_reports_document_cache_hit_and_miss_events(tmp_path):
    document = DocumentInput(document_id="doc-1", title="Doc", text="Action: owner should reply by 2026-07-04.")
    pipeline = BriefingPipeline(
        cache_config=CacheConfig(cache_dir=str(tmp_path / "cache"), output_cache=False),
        summarizer=RuleBasedExtractiveSummarizer(),
    )

    first = pipeline.run([document])
    second = pipeline.run([document])

    first_event = first.stats.document_cache_events[0]
    second_event = second.stats.document_cache_events[0]
    assert first_event.document_id == "doc-1"
    assert first_event.status == "miss"
    assert first_event.reason == "miss_new_fingerprint"
    assert first_event.fingerprint_prefix
    assert first_event.cache_key_prefix
    assert second_event.status == "hit"
    assert second_event.reason == "hit_same_contract"


def test_pipeline_reports_document_cache_policy_events(tmp_path):
    document = DocumentInput(document_id="doc-1", title="Doc", text="Action: owner should reply by 2026-07-04.")

    for policy, status, reason in [
        ("refresh", "refresh", "miss_refresh_policy"),
        ("bypass", "bypass", "miss_bypass_policy"),
        ("ephemeral", "ephemeral", "miss_ephemeral_policy"),
    ]:
        pipeline = BriefingPipeline(
            cache_config=CacheConfig(cache_dir=str(tmp_path / policy), policy=policy, output_cache=False),
            summarizer=RuleBasedExtractiveSummarizer(),
        )

        result = pipeline.run([document])

        event = result.stats.document_cache_events[0]
        assert event.status == status
        assert event.reason == reason


def test_pipeline_reports_output_cache_event(tmp_path):
    document = DocumentInput(document_id="doc-1", title="Doc", text="Action: owner should reply by 2026-07-04.")
    pipeline = BriefingPipeline(
        cache_config=CacheConfig(cache_dir=str(tmp_path / "cache"), output_cache=True),
        summarizer=RuleBasedExtractiveSummarizer(),
    )

    first = pipeline.run([document])
    second = pipeline.run([document])

    assert first.stats.output_cache_event is not None
    assert first.stats.output_cache_event.status == "miss"
    assert first.stats.output_cache_event.reason == "output_miss"
    assert second.stats.output_cache_event is not None
    assert second.stats.output_cache_event.status == "hit"
    assert second.stats.output_cache_event.reason == "output_hit_same_render_key"
