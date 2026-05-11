from pathlib import Path

from document_briefing_cache import __version__
from document_briefing_cache.pipeline import SKILL_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_versions_are_synchronized_to_0_2_0():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'version = "0.2.0"' in pyproject
    assert __version__ == "0.2.0"
    assert SKILL_VERSION == "0.2.0"
    assert 'version: "0.2.0"' in openai_yaml


def test_openai_yaml_uses_interface_metadata():
    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert "interface:" in openai_yaml
    assert 'display_name: "Document Briefing Cache"' in openai_yaml
    assert 'short_description: "Cached structured document briefings"' in openai_yaml
    assert "$document-briefing-cache" in openai_yaml
    assert "policy:" in openai_yaml
    assert "allow_implicit_invocation: true" in openai_yaml


def test_skill_description_matches_supported_modes_and_boundary():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    frontmatter = skill.split("---", 2)[1]
    assert "compare" not in frontmatter
    assert "source-code review/debugging" in frontmatter
    assert "code-review notes or PR discussion documents" in skill
    assert "Tradeoff:" in skill
