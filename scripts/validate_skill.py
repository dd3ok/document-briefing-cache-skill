from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    "src/document_briefing_cache/models.py",
    "src/document_briefing_cache/pipeline.py",
    "src/document_briefing_cache/summarizers.py",
    "templates/brief.md.j2",
    "templates/executive.md.j2",
    "templates/action_items.md.j2",
    "templates/digest.md.j2",
    "templates/debug.md.j2",
    "examples/mixed_documents.json",
]

REQUIRED_SKILL_TERMS = [
    "DocumentSummaryState",
    "content_fingerprint",
    "cache",
    "template",
    "LLM only",
    "same document",
]


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"Missing required file: {rel}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not re.search(r"---\s*\nname:\s*document-briefing-cache", skill):
        errors.append("SKILL.md must include metadata name: document-briefing-cache")
    if "description:" not in skill.split("---", 2)[1]:
        errors.append("SKILL.md metadata must include description")
    for term in REQUIRED_SKILL_TERMS:
        if term not in skill:
            errors.append(f"SKILL.md should mention: {term}")
    if "news only" in skill.lower():
        errors.append("Skill should not be scoped to news only.")

    template_dir = ROOT / "templates"
    modes = {path.stem.replace(".md", "") for path in template_dir.glob("*.md.j2")}
    expected_modes = {"brief", "executive", "action_items", "digest", "debug"}
    missing_modes = expected_modes - modes
    if missing_modes:
        errors.append(f"Missing templates for modes: {sorted(missing_modes)}")

    tests = list((ROOT / "tests").glob("test_*.py"))
    if len(tests) < 4:
        errors.append("Expected at least four test files.")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: document briefing cache skill repository validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
