from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline


def test_brief_rendering_contains_sections(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Decision: proceed. Action: owner should follow up. Risk: delay possible.")]
    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="brief", use_output_cache=False)
    assert "문서 브리핑" in result.output
    assert "액션 아이템" in result.output
    assert "리스크" in result.output


def test_action_items_template(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Action: Backend team should patch the API. Owner: Backend. Due: 2026-05-10.")]
    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="action_items", use_output_cache=False)
    assert "액션 아이템 중심" in result.output
    assert "Backend" in result.output


def test_debug_template_shows_cache_stats(tmp_path):
    docs = [DocumentInput(document_id="x", title="X", text="Hello 123")]
    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="debug", use_output_cache=False)
    assert "Cache Stats" in result.output
    assert "summarizer_calls" in result.output
