from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_trigger_eval_fixture_and_scope():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "trigger_eval_cases.json" in readme
    assert "static boundary fixtures" in readme
    assert "not measure actual model-side invocation behavior" in readme


def test_readme_includes_claude_ai_description_variant_under_200_chars():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "Claude.ai description variant:"
    start = readme.index(marker) + len(marker)
    description = readme[start:].split("\n", 1)[0].strip()

    assert description
    assert len(description) <= 200


def test_agents_documents_sensitive_cache_defaults():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "ephemeral" in agents
    assert "no output cache" in agents
    assert "PII redaction" in agents
    assert "HMAC" in agents


def test_readme_documents_local_path_and_url_metadata_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "--input" in readme
    assert "local file path" in readme
    assert "does not fetch URLs" in readme
    assert "URL-bearing metadata" in readme
    assert "URL-bearing metadata" in skill
    assert "file paths, URLs" not in skill.split("---", 2)[1]
