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
    "src/document_briefing_cache/templates/brief.md.j2",
    "src/document_briefing_cache/templates/executive.md.j2",
    "src/document_briefing_cache/templates/action_items.md.j2",
    "src/document_briefing_cache/templates/digest.md.j2",
    "src/document_briefing_cache/templates/debug.md.j2",
    "examples/mixed_documents.json",
    "evals/briefing_eval_cases.json",
    "evals/trigger_eval_cases.json",
    "evals/model_invocation_benchmark_cases.json",
    "agents/openai.yaml",
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
    if "compare" in skill.split("---", 2)[1].lower():
        errors.append("SKILL.md metadata should not mention compare unless a compare mode exists.")

    template_dir = ROOT / "src" / "document_briefing_cache" / "templates"
    modes = {path.stem.replace(".md", "") for path in template_dir.glob("*.md.j2")}
    expected_modes = {"brief", "executive", "action_items", "digest", "debug"}
    missing_modes = expected_modes - modes
    if missing_modes:
        errors.append(f"Missing templates for modes: {sorted(missing_modes)}")

    tests = list((ROOT / "tests").glob("test_*.py"))
    if len(tests) < 4:
        errors.append("Expected at least four test files.")
    errors.extend(validate_imports())
    errors.extend(validate_openai_yaml(ROOT / "agents" / "openai.yaml"))
    eval_path = ROOT / "evals" / "briefing_eval_cases.json"
    eval_payload, eval_errors = validate_eval_cases(eval_path)
    errors.extend(eval_errors)
    trigger_eval_payload, trigger_eval_errors = validate_trigger_eval_cases(ROOT / "evals" / "trigger_eval_cases.json")
    errors.extend(trigger_eval_errors)
    invocation_payload, invocation_errors = validate_model_invocation_benchmark_cases(ROOT / "evals" / "model_invocation_benchmark_cases.json")
    errors.extend(invocation_errors)
    if args.run_evals and eval_payload is not None:
        errors.extend(run_eval_cases(eval_payload))
    if args.run_evals and trigger_eval_payload is not None:
        errors.extend(run_trigger_eval_cases(trigger_eval_payload))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: document briefing cache skill repository validated "
        f"({len(tests)} test files, {len((eval_payload or {}).get('cases', []))} eval cases, "
        f"{len((trigger_eval_payload or {}).get('cases', []))} trigger cases, "
        f"{len((invocation_payload or {}).get('cases', []))} model benchmark cases)"
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
    if not isinstance(cases, list) or len(cases) < 5:
        return payload, ["Eval fixture should contain at least five cases."]
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
            if run.get("mode") not in {"brief", "executive", "action_items", "digest", "debug"}:
                errors.append(f"{run_prefix} has invalid mode.")
            if "summarizer_calls" not in stats:
                errors.append(f"{run_prefix} missing expect.stats.summarizer_calls.")
            if "document_cache_hits" not in stats:
                errors.append(f"{run_prefix} missing expect.stats.document_cache_hits.")
            state_expect = expected.get("summary_state", {})
            if state_expect and not isinstance(state_expect, dict):
                errors.append(f"{run_prefix} expect.summary_state should be an object.")
    return payload, errors


def validate_trigger_eval_cases(path: Path) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, [f"Missing trigger eval fixture: {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"Trigger eval fixture is not valid JSON: {exc}"]
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 8:
        return payload, ["Trigger eval fixture should contain at least eight cases."]
    errors = []
    has_positive = False
    has_negative = False
    allowed_input_kinds = {"inline_document", "cached_state", "no_document", "source_code", "stack_trace", "plain_text"}
    allowed_negative_boundaries = {"live_research", "source_code_review", "debugging", "general_writing", "translation_only", "simple_qa", "no_document_input"}
    required_negative_boundaries = {"live_research", "source_code_review", "debugging", "translation_only", "simple_qa"}
    seen_negative_boundaries: set[str] = set()
    for idx, case in enumerate(cases):
        prefix = f"Trigger eval case {idx}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} should be an object.")
            continue
        input_payload = case.get("input")
        expect = case.get("expect")
        if not case.get("id"):
            errors.append(f"{prefix} missing id.")
        if not case.get("prompt"):
            errors.append(f"{prefix} missing prompt.")
        if not isinstance(input_payload, dict):
            errors.append(f"{prefix} missing input object.")
            continue
        if input_payload.get("kind") not in allowed_input_kinds:
            errors.append(f"{prefix} has invalid input.kind.")
        if not isinstance(expect, dict):
            errors.append(f"{prefix} missing expect object.")
            continue
        if not isinstance(expect.get("invoke"), bool):
            errors.append(f"{prefix} missing boolean expect.invoke.")
            continue
        if expect.get("invoke") is True:
            has_positive = True
            if input_payload.get("kind") not in {"inline_document", "cached_state"}:
                errors.append(f"{prefix} positive trigger should use document-like input or cached state.")
            if not expect.get("intent"):
                errors.append(f"{prefix} positive trigger missing expect.intent.")
        if expect.get("invoke") is False:
            has_negative = True
            boundary = str(expect.get("boundary"))
            if boundary not in allowed_negative_boundaries:
                errors.append(f"{prefix} has invalid expect.boundary.")
            seen_negative_boundaries.add(boundary)
    if not has_positive:
        errors.append("Trigger eval fixture must include positive cases.")
    if not has_negative:
        errors.append("Trigger eval fixture must include negative cases.")
    missing_boundaries = required_negative_boundaries - seen_negative_boundaries
    if missing_boundaries:
        errors.append(f"Trigger eval fixture missing negative boundaries: {sorted(missing_boundaries)}")
    return payload, errors


def validate_openai_yaml(path: Path) -> list[str]:
    if not path.exists():
        return [f"Missing agents metadata: {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8")
    errors = []
    required_fragments = [
        'version: "0.3.1"',
        "interface:",
        'display_name: "Document Briefing Cache"',
        'short_description: "Rerender cached structured briefings without re-summarizing unchanged documents."',
        "$document-briefing-cache",
        "policy:",
        "allow_implicit_invocation: true",
        'name: "document-briefing-cache"',
    ]
    for fragment in required_fragments:
        if fragment not in text:
            errors.append(f"agents/openai.yaml missing required metadata fragment: {fragment}")
    return errors


def validate_model_invocation_benchmark_cases(path: Path) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, [f"Missing model invocation benchmark fixture: {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"Model invocation benchmark fixture is not valid JSON: {exc}"]
    return payload, validate_model_invocation_benchmark_cases_from_payload(payload, path)


def validate_model_invocation_benchmark_cases_from_payload(payload: dict, path: Path) -> list[str]:
    errors = []
    if payload.get("manual") is not True:
        errors.append(f"{path.relative_to(ROOT)} must set manual=true because model invocation telemetry is host-specific.")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 4:
        return errors + ["Model invocation benchmark fixture should contain at least four cases."]
    has_positive = False
    has_negative = False
    for idx, case in enumerate(cases):
        prefix = f"Model invocation benchmark case {idx}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} should be an object.")
            continue
        if not case.get("id"):
            errors.append(f"{prefix} missing id.")
        if not case.get("prompt"):
            errors.append(f"{prefix} missing prompt.")
        if not isinstance(case.get("expected_invocation"), bool):
            errors.append(f"{prefix} missing boolean expected_invocation.")
            continue
        has_positive = has_positive or case["expected_invocation"]
        has_negative = has_negative or not case["expected_invocation"]
        if "observed_invocation" not in case:
            errors.append(f"{prefix} missing observed_invocation.")
        elif case.get("observed_invocation") is not None and (
            not case.get("host") or not case.get("model") or not case.get("date")
        ):
            errors.append(f"{prefix} with observed_invocation must include host, model, and date.")
        if "host" not in case or "model" not in case or "date" not in case or "notes" not in case:
            errors.append(f"{prefix} must include host, model, date, and notes fields.")
    if not has_positive:
        errors.append("Model invocation benchmark fixture must include positive expected cases.")
    if not has_negative:
        errors.append("Model invocation benchmark fixture must include negative expected cases.")
    return errors


def run_eval_cases(payload: dict) -> list[str]:
    from document_briefing_cache.models import CacheConfig, DocumentInput
    from document_briefing_cache.pipeline import BriefingPipeline

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dbc-evals-") as cache_dir:
        for case in payload.get("cases", []):
            documents = [DocumentInput.model_validate(document) for document in case.get("input", {}).get("documents", [])]
            input_config = case.get("input", {})
            policy = input_config.get("cache_policy", "read_write")
            pipeline = BriefingPipeline(
                cache_config=CacheConfig(
                    cache_dir=cache_dir,
                    policy=policy,
                    output_cache=True,
                    redact_pii=bool(input_config.get("redact_pii", False)),
                )
            )
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
                errors.extend(validate_summary_state_expectations(case["id"], run["id"], result.summaries, expect.get("summary_state", {})))
    return errors


def validate_summary_state_expectations(case_id: str, run_id: str, summaries, expectations: dict) -> list[str]:
    if not expectations:
        return []
    fields = collect_summary_state_fields(summaries)
    errors = []
    for field, needles in expectations.items():
        if field not in fields:
            errors.append(f"{case_id}:{run_id} has unsupported summary_state expectation {field!r}")
            continue
        haystack = "\n".join(fields[field])
        for needle in needles:
            if needle not in haystack:
                errors.append(f"{case_id}:{run_id} summary_state.{field} missing {needle!r}")
    return errors


def collect_summary_state_fields(summaries) -> dict[str, list[str]]:
    actions = []
    risks = []
    metrics = []
    unknowns = []
    evidence = []
    entities = []
    for summary in summaries:
        entities.extend(summary.entities)
        unknowns.extend(summary.unknowns)
        for action in summary.actions:
            actions.extend([action.action, action.owner or "", action.due or ""])
            evidence.extend(ref.quote or "" for ref in action.evidence)
        for risk in summary.risks:
            risks.extend([risk.title, risk.reason or "", risk.severity])
            evidence.extend(ref.quote or "" for ref in risk.evidence)
        for metric in summary.metrics:
            metrics.extend([metric.name or "", metric.value, metric.unit or ""])
            evidence.extend(ref.quote or "" for ref in metric.evidence)
        for point in summary.key_points:
            evidence.extend(ref.quote or "" for ref in point.evidence)
        for decision in summary.decisions:
            evidence.extend(ref.quote or "" for ref in decision.evidence)
    return {
        "actions_contains": actions,
        "risks_contains": risks,
        "metrics_contains": metrics,
        "unknowns_contains": unknowns,
        "evidence_contains": evidence,
        "entities_contains": entities,
    }


def run_trigger_eval_cases(payload: dict) -> list[str]:
    errors = []
    for case in payload.get("cases", []):
        actual = infer_skill_trigger_for_eval(case)
        expected = bool(case.get("expect", {}).get("invoke"))
        if actual != expected:
            errors.append(f"{case.get('id')} expected invoke={expected}, got {actual}")
    return errors


def infer_skill_trigger_for_eval(case: dict) -> bool:
    prompt = str(case.get("prompt", ""))
    input_payload = case.get("input", {}) if isinstance(case.get("input"), dict) else {}
    kind = input_payload.get("kind")
    lowered = prompt.lower()
    negative_terms = (
        "최신",
        "오늘",
        "찾아서",
        "live",
        "current",
        "코드 리뷰",
        "버그를 찾아",
        "debug",
        "디버깅",
        "stack trace",
        "번역만",
        "translate only",
        "어디에 저장",
        "무엇",
        "what is",
    )
    positive_terms = (
        "summarize",
        "brief",
        "회의록",
        "문서",
        "json",
        "xml",
        "payload",
        "리포트",
        "로그",
        "티켓",
        "transcript",
        "재렌더",
        "rerender",
        "digest",
        "액션",
        "리뷰 코멘트",
        "pr 리뷰",
    )
    if any(term in lowered for term in negative_terms):
        return False
    return kind in {"inline_document", "cached_state"} and any(term in lowered for term in positive_terms)


if __name__ == "__main__":
    raise SystemExit(main())
