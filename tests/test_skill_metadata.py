from pathlib import Path

from document_briefing_cache import __version__
from document_briefing_cache.pipeline import SKILL_VERSION


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "briefprint" / "SKILL.md"
OPENAI_SHORT_DESCRIPTION = (
    'short_description: "Rerender cached document briefings without re-summarizing unchanged supplied documents."'
)


def test_versions_are_synchronized_to_0_4_0():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'version = "0.4.0"' in pyproject
    assert __version__ == "0.4.0"
    assert SKILL_VERSION == "0.4.0"
    assert 'version: "0.4.0"' in openai_yaml


def test_openai_yaml_uses_interface_metadata():
    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert "interface:" in openai_yaml
    assert 'display_name: "Briefprint"' in openai_yaml
    assert OPENAI_SHORT_DESCRIPTION in openai_yaml
    assert "$briefprint" in openai_yaml
    assert 'name: "briefprint"' in openai_yaml
    assert "policy:" in openai_yaml
    assert "allow_implicit_invocation: false" in openai_yaml
    assert "invocation_examples:" in openai_yaml
    assert "$briefprint summarize supplied documents into a cached briefing" in openai_yaml
    assert "$briefprint rerender cached briefing as digest" in openai_yaml
    assert "triggers:" not in openai_yaml
    for broad_trigger in [
        "summarize these supplied documents",
        "summarize this JSON or XML payload",
        "create an executive digest for this document set",
    ]:
        assert broad_trigger not in openai_yaml


def test_root_and_installable_openai_yaml_are_identical():
    root_openai_yaml = (ROOT / "agents" / "openai.yaml").read_bytes()
    installable_openai_yaml = (ROOT / "skills" / "briefprint" / "agents" / "openai.yaml").read_bytes()

    assert root_openai_yaml == installable_openai_yaml


def test_skill_description_matches_supported_modes_and_boundary():
    skill = SKILL.read_text(encoding="utf-8")

    frontmatter = skill.split("---", 2)[1]
    description = next(
        line.split(":", 1)[1].strip().strip('"') for line in frontmatter.splitlines() if line.startswith("description:")
    )
    assert "disable-model-invocation: true" in frontmatter
    assert len(description) <= 420
    description_lower = description.lower()
    assert "explicitly invoked" in description_lower
    assert "briefprint, $briefprint, or /briefprint" in description_lower
    assert "ordinary one-off summaries" in description_lower
    for term in ["summarize", "brief", "digest", "recap", "rerender", "cached briefing state"]:
        assert term in description_lower
    for input_kind in ["documents", "notes", "tickets", "logs", "reports", "transcripts", "json/xml/api payloads"]:
        assert input_kind in description_lower
    for boundary in [
        "live research",
        "source-code review/debugging",
        "general writing",
        "translation-only",
        "simple q&a",
    ]:
        assert boundary in description_lower
    assert "cacheable" in description_lower
    assert "input" in description_lower
    assert "compare" not in frontmatter
    assert "source-code review/debugging" in frontmatter
    assert "code-review notes or PR discussion documents" in skill
    assert "Tradeoff:" in skill


def test_repository_root_is_not_installable_as_agent_skill():
    assert not (ROOT / "SKILL.md").exists()
