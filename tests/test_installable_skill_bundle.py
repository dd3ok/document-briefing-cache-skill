from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "skills" / "document-briefing-cache"


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
    assert name == "document-briefing-cache"
    assert re.fullmatch(r"[a-z0-9-]{1,64}", name)
    assert description
    assert len(description) <= 1024

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

    assert "skills/document-briefing-cache" in doc
    assert "Do not install the repository root" in doc
    assert "~/.codex/skills" not in doc
    assert "npx skills install" not in doc
    assert "npx skills add" in doc
    for vendor in ["Codex", "Claude Code", "Gemini CLI", "Antigravity", "OpenClaw", "Hermes"]:
        assert vendor in doc


def _frontmatter_value(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, flags=re.MULTILINE)
    assert match is not None, key
    return match.group(1).strip().strip('"')
