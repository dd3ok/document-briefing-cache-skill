from importlib import resources
from pathlib import Path

from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline


ROOT = Path(__file__).resolve().parents[1]


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


def test_wheel_install_surface_is_runtime_only():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert 'where = ["src"]' in pyproject
    assert 'document_briefing_cache = ["templates/*.md.j2"]' in pyproject

    assert "include README.md README.ko.md LICENSE AGENTS.md SKILL.md VALIDATION.md" not in manifest
    assert "include README.md README.ko.md LICENSE AGENTS.md VALIDATION.md" in manifest
    assert "recursive-include skills *.md *.yaml" in manifest
