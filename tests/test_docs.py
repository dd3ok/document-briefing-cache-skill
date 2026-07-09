from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "briefprint" / "SKILL.md"


def test_readme_documents_trigger_eval_fixture_and_scope():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "trigger_eval_cases.json" in readme
    assert "static boundary fixtures" in readme
    assert "not measure actual model-side invocation behavior" in readme


def test_readme_documents_briefprint_skill_branding():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# Briefprint")
    assert "Read once. Brief anywhere." in readme
    assert "github.com/dd3ok/briefprint" in readme
    assert "briefprint` agent skill" in readme
    assert "briefprint-skill" not in readme


def test_readme_links_korean_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")

    assert "[한국어](README.ko.md)" in readme
    assert "[English](README.md)" in korean
    assert "한 번 읽고, 어디서든 브리핑하세요." in korean


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

    assert "basic-contact-v2" in combined
    assert "email" in combined
    assert "Korean mobile" in combined
    assert "Korean resident or foreigner registration number" in combined
    assert "US phone" in combined
    assert "not a complete PII detector" in combined
    assert "--cache-policy ephemeral" in combined
    assert "--no-output-cache" in combined
    assert "encrypted storage" in combined
    assert "tmpfs" in combined
    assert "tamper detection only" in combined
    assert "not encryption" in combined


def test_readmes_document_limits_and_alternative_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")

    assert "## Limits And Alternatives" in readme
    assert "Kakao or Naver account IDs" in readme
    assert "bank account numbers remain out of scope" in readme
    assert "no cross-process file lock" in readme
    assert "The built-in CLI LLM adapter is OpenAI-only" in readme
    assert "CacheBackedEmbeddings caches embedding calculations by text hash" in readme
    assert "not a structured document-summary cache" in readme
    assert "provider prompt caching is complementary" in readme

    assert "## 한계와 대안" in korean
    assert "카카오나 네이버 계정 ID" in korean
    assert "주민등록번호/외국인등록번호" in korean
    assert "계좌번호는 범위 밖" in korean
    assert "프로세스 간 파일 lock은 없습니다" in korean
    assert "CLI 내장 LLM adapter는 OpenAI 전용" in korean
    assert "CacheBackedEmbeddings는 텍스트 해시로 embedding 계산 결과를 캐시" in korean
    assert "구조화 문서 요약 캐시는 아닙니다" in korean
    assert "provider prompt caching은 보완 관계" in korean


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


def test_root_best_practices_documents_sensitive_and_secret_redaction():
    best_practices = (ROOT / "references" / "best-practices.md").read_text(encoding="utf-8")

    assert "--sensitive" in best_practices
    assert "--redact-secrets" in best_practices
    assert "basic-secrets-v1" in best_practices
    assert "not included in `--sensitive`" in best_practices
    assert "HMAC signing is tamper detection only, not encryption" in best_practices


def test_competitive_roadmap_status_is_not_stale_proposed_snapshot():
    roadmap = (ROOT / "references" / "competitive-roadmap.md").read_text(encoding="utf-8")

    assert "Status: implemented through P5; deferred items remain" in roadmap
    assert "Current implementation status" in roadmap


def test_readmes_document_skill_and_runtime_naming_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")

    assert "Agent skill: `briefprint`" in readme
    assert "Python package/CLI: `document-briefing-cache` / `document_briefing_cache`" in readme
    assert "에이전트 스킬: `briefprint`" in korean
    assert "Python 패키지/CLI: `document-briefing-cache` / `document_briefing_cache`" in korean


def test_readmes_document_host_specific_explicit_skill_invocation():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")

    assert "Codex, use `$briefprint`; for Claude Code, use `/briefprint`" in readme
    assert "host's explicit skill invocation" in readme
    assert "Codex에서는 `$briefprint`, Claude Code에서는 `/briefprint`" in korean
    assert "호스트의 명시적 스킬 호출" in korean


def test_best_practices_avoid_implicit_trigger_language():
    root_best_practices = (ROOT / "references" / "best-practices.md").read_text(encoding="utf-8")
    skill_best_practices = (ROOT / "skills" / "briefprint" / "references" / "best-practices.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([root_best_practices, skill_best_practices])

    assert "clear invocation examples and boundaries" in combined
    assert "description for discoverability and manual invocation guidance" in combined
    assert "trigger phrases" not in combined
    assert "precise triggering" not in combined


def test_secret_redaction_docs_warn_about_operational_correlation_ids():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")
    best_practices = (ROOT / "references" / "best-practices.md").read_text(encoding="utf-8")
    skill_best_practices = (ROOT / "skills" / "briefprint" / "references" / "best-practices.md").read_text(encoding="utf-8")

    assert "session_id" in readme
    assert "operational correlation" in readme
    assert "session_id" in korean
    assert "운영 상관관계" in korean
    assert "session_id" in best_practices
    assert "session_id" in skill_best_practices


def test_docs_separate_agent_skill_bundle_from_runtime_cache():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    korean = (ROOT / "README.ko.md").read_text(encoding="utf-8")
    install = (ROOT / "docs" / "agent-skill-installation.md").read_text(encoding="utf-8")
    skill_best_practices = (ROOT / "skills" / "briefprint" / "references" / "best-practices.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([readme, korean, install, skill_best_practices])

    assert "skill bundle is static" in combined
    assert "runtime cache lives under `--cache-dir`" in combined
    assert "Installing, updating, or removing the agent skill does not migrate, prune, or delete runtime caches" in combined
    assert "No portable agent-skill host contract currently provides automatic eviction for generated document state" in combined
    assert "Do not write document caches into the installed skill directory" in combined
