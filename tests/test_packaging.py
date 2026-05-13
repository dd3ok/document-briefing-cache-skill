from importlib import resources

from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline


def test_templates_are_packaged_resources():
    template_root = resources.files("document_briefing_cache").joinpath("templates")
    names = {path.name for path in template_root.iterdir()}

    assert {
        "brief.md.j2",
        "executive.md.j2",
        "action_items.md.j2",
        "digest.md.j2",
        "debug.md.j2",
    }.issubset(names)


def test_default_renderer_uses_packaged_templates(tmp_path):
    docs = [
        DocumentInput(
            document_id="pkg",
            title="Packaging",
            text="Action: Release worker should package templates.",
        )
    ]

    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="brief", use_output_cache=False)

    assert "문서 브리핑" in result.output
    assert "Packaging" in result.output
