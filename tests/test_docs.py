from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "document-briefing-cache" / "SKILL.md"


def test_readme_documents_trigger_eval_fixture_and_scope():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "trigger_eval_cases.json" in readme
    assert "static boundary fixtures" in readme
    assert "not measure actual model-side invocation behavior" in readme


def test_readme_uses_briefprint_brand_without_renaming_skill():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# Briefprint")
    assert "Read once. Brief anywhere." in readme
    assert "github.com/dd3ok/briefprint" in readme
    assert "document-briefing-cache` agent skill" in readme
    assert "document-briefing-cache-skill" not in readme


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
    skill = SKILL.read_text(encoding="utf-8")

    assert "--input" in readme
    assert "local file path" in readme
    assert "does not fetch URLs" in readme
    assert "URL-bearing metadata" in readme
    assert "URL-bearing metadata" in skill
    assert "file paths, URLs" not in skill.split("---", 2)[1]


def test_readme_documents_redaction_scope_and_security_limits():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = SKILL.read_text(encoding="utf-8")
    best_practices = (ROOT / "references" / "best-practices.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, skill, best_practices])

    assert "basic-contact-v1" in combined
    assert "email" in combined
    assert "Korean mobile" in combined
    assert "US phone" in combined
    assert "not a complete PII detector" in combined
    assert "--cache-policy ephemeral" in combined
    assert "--no-output-cache" in combined
    assert "encrypted storage" in combined
    assert "tmpfs" in combined
    assert "tamper detection only" in combined
    assert "not encryption" in combined


def test_readme_documents_secret_redaction_scope_and_sensitive_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "--redact-secrets" in readme
    assert "basic-secrets-v1" in readme
    assert "bearer tokens" in readme
    assert "API keys" in readme
    assert "webhook URLs" in readme
    assert "card-like values" in readme
    assert "secret-shaped JSON keys" in readme
    assert "best-effort" in readme
    assert "not included in --sensitive" in readme
