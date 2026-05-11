from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
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
    "evals/briefing_eval_cases.json",
]

REQUIRED_SKILL_TERMS = [
    "DocumentSummaryState",
    "content_fingerprint",
    "cache",
    "template",
    "LLM only",
    "same document",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the document briefing cache skill bundle.")
    parser.add_argument("--run-evals", action="store_true", help="Execute compact eval fixtures with the rules summarizer.")
    args = parser.parse_args(argv)

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
    errors.extend(validate_imports())
    eval_path = ROOT / "evals" / "briefing_eval_cases.json"
    eval_payload, eval_errors = validate_eval_cases(eval_path)
    errors.extend(eval_errors)
    if args.run_evals and eval_payload is not None:
        errors.extend(run_eval_cases(eval_payload))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: document briefing cache skill repository validated "
        f"({len(tests)} test files, {len((eval_payload or {}).get('cases', []))} eval cases)"
    )
    return 0


def validate_imports() -> list[str]:
    sys.path.insert(0, str(ROOT / "src"))
    try:
        import document_briefing_cache  # noqa: F401
        from document_briefing_cache.models import DocumentInput  # noqa: F401
        from document_briefing_cache.pipeline import BriefingPipeline  # noqa: F401
    except Exception as exc:
        return [f"Package import failed: {exc}"]
    return []


def validate_eval_cases(path: Path) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, [f"Missing eval fixture: {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"Eval fixture is not valid JSON: {exc}"]
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 4:
        return payload, ["Eval fixture should contain at least four cases."]
    errors = []
    for idx, case in enumerate(cases):
        prefix = f"Eval case {idx}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} should be an object.")
            continue
        runs = case.get("runs")
        if not case.get("id"):
            errors.append(f"{prefix} missing id.")
        if not isinstance(case.get("input"), dict) or "documents" not in case["input"]:
            errors.append(f"{prefix} missing input.documents.")
        if not isinstance(runs, list) or not runs:
            errors.append(f"{prefix} missing runs.")
            continue
        for run_idx, run in enumerate(runs):
            run_prefix = f"{prefix} run {run_idx}"
            expected = run.get("expect", {}) if isinstance(run, dict) else {}
            stats = expected.get("stats", {}) if isinstance(expected, dict) else {}
            if not run.get("id"):
                errors.append(f"{run_prefix} missing id.")
            if not run.get("prompt"):
                errors.append(f"{run_prefix} missing prompt.")
            if run.get("mode") not in {"brief", "executive", "action_items", "digest", "debug", "none"}:
                errors.append(f"{run_prefix} has invalid mode.")
            if "summarizer_calls" not in stats:
                errors.append(f"{run_prefix} missing expect.stats.summarizer_calls.")
            if "document_cache_hits" not in stats:
                errors.append(f"{run_prefix} missing expect.stats.document_cache_hits.")
    return payload, errors


def run_eval_cases(payload: dict) -> list[str]:
    from document_briefing_cache.models import CacheConfig, DocumentInput
    from document_briefing_cache.pipeline import BriefingPipeline

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dbc-evals-") as cache_dir:
        for case in payload.get("cases", []):
            documents = [DocumentInput.model_validate(document) for document in case.get("input", {}).get("documents", [])]
            policy = case.get("input", {}).get("cache_policy", "read_write")
            pipeline = BriefingPipeline(cache_config=CacheConfig(cache_dir=cache_dir, policy=policy, output_cache=True))
            for run in case.get("runs", []):
                if run.get("mode") == "none":
                    continue
                result = pipeline.run(documents, mode=run.get("mode", "brief"), use_output_cache=run.get("use_output_cache"))
                expect = run.get("expect", {})
                for stat_name, expected_value in expect.get("stats", {}).items():
                    actual_value = getattr(result.stats, stat_name)
                    if actual_value != expected_value:
                        errors.append(f"{case['id']}:{run['id']} expected {stat_name}={expected_value}, got {actual_value}")
                for needle in expect.get("contains", []):
                    if needle not in result.output:
                        errors.append(f"{case['id']}:{run['id']} output missing {needle!r}")
                for needle in expect.get("not_contains", []):
                    if needle in result.output:
                        errors.append(f"{case['id']}:{run['id']} output unexpectedly contained {needle!r}")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
