from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "skills" / "briefprint"


def test_installable_skill_bundle_contains_only_skill_surface():
    assert not (ROOT / "SKILL.md").exists()
    assert (BUNDLE / "SKILL.md").is_file()
    assert (BUNDLE / "agents" / "openai.yaml").is_file()
    assert (BUNDLE / "references").is_dir()

    forbidden_dirs = {
        ".github",
        "docs",
        "evals",
        "examples",
        "scripts",
        "src",
        "tests",
    }
    present_forbidden = [name for name in forbidden_dirs if (BUNDLE / name).exists()]
    assert present_forbidden == []

    files = [path.relative_to(BUNDLE).as_posix() for path in BUNDLE.rglob("*") if path.is_file()]
    assert len(files) <= 8
    assert all(not file.endswith((".py", ".json", ".toml")) for file in files)


def test_installable_skill_bundle_frontmatter_and_references_are_portable():
    skill = (BUNDLE / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)[1]

    name = _frontmatter_value(frontmatter, "name")
    description = _frontmatter_value(frontmatter, "description")
    assert name == "briefprint"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", name)
    assert description
    assert len(description) <= 1024
    assert len(description) <= 420
    assert _frontmatter_value(frontmatter, "disable-model-invocation") == "true"

    root_only_fragments = [
        "src/",
        "tests/",
        "evals/",
        "examples/",
        "scripts/",
        "VALIDATION.md",
        "pyproject.toml",
        "pip install",
    ]
    for fragment in root_only_fragments:
        assert fragment not in skill

    for reference in re.findall(r"`(references/[^`]+\.md)`", skill):
        reference_path = BUNDLE / reference
        assert reference_path.is_file(), reference
        assert reference_path.parent == BUNDLE / "references"


def test_agent_skill_installation_doc_covers_lightweight_vendor_paths():
    doc = (ROOT / "docs" / "agent-skill-installation.md").read_text(encoding="utf-8")

    assert "skills/briefprint" in doc
    assert "dd3ok/briefprint" in doc
    assert "Do not install the repository root" in doc
    assert "~/.codex/skills" not in doc
    assert "npx skills install" not in doc
    for section in [
        "Verified surfaces",
        "Community-compatible notes",
        "Verify installed files",
    ]:
        assert section in doc
    assert re.search(r"Last checked: \d{4}-\d{2}-\d{2}", doc)
    assert "Codex local and repository skill folders" in doc
    assert "Claude Code personal and project skill folders" in doc
    for vendor in ["Codex", "Claude Code", "Gemini CLI", "Antigravity", "OpenClaw", "Hermes"]:
        assert vendor in doc

    community_notes = doc.split("## Community-compatible notes", 1)[1].split("## Bundle Contents", 1)[0]
    for vendor in ["Gemini CLI", "Antigravity", "OpenClaw", "Hermes"]:
        assert vendor in community_notes
        assert f"## {vendor}" not in doc
    assert "skills/briefprint" in community_notes
    assert "repository root" in community_notes
    assert "verify" in community_notes.lower()
    assert "SKILL.md" in community_notes
    assert "agents/openai.yaml" in community_notes
    assert "references/*.md" in community_notes


def test_validate_skill_reports_missing_installable_skill_without_crashing(tmp_path):
    module = _load_validate_skill_module()
    missing_skill = tmp_path / "briefprint" / "SKILL.md"

    errors = module.validate_installable_skill_metadata(missing_skill)

    assert len(errors) == 1
    assert "Missing installable skill metadata" in errors[0]
    assert "SKILL.md" in errors[0]


def _frontmatter_value(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, flags=re.MULTILINE)
    assert match is not None, key
    return match.group(1).strip().strip('"')


def _load_validate_skill_module():
    path = ROOT / "scripts" / "validate_skill.py"
    spec = importlib.util.spec_from_file_location("validate_skill_for_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
