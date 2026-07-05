import json
from pathlib import Path

from scripts.validate_skill import run_trigger_eval_cases, validate_trigger_eval_cases


ROOT = Path(__file__).resolve().parents[1]


def test_trigger_eval_fixture_covers_positive_and_negative_boundaries():
    path = ROOT / "evals" / "trigger_eval_cases.json"
    payload, errors = validate_trigger_eval_cases(path)

    assert errors == []
    cases = payload["cases"]
    positives = [case for case in cases if case["expect"]["invoke"]]
    negatives = [case for case in cases if not case["expect"]["invoke"]]
    assert len(positives) >= 4
    assert len(negatives) >= 5
    assert all("briefprint" in case["prompt"].lower() for case in positives)
    assert any(case["expect"].get("boundary") == "source_code_review" for case in negatives)
    assert any(case["expect"].get("boundary") == "translation_only" for case in negatives)
    assert any(case["expect"].get("boundary") == "ordinary_one_off_summary" for case in negatives)
    assert any(case["expect"].get("intent") == "summarize_review_comments" for case in positives)
    assert any(case["prompt"] == "Summarize these meeting notes and extract action items." for case in cases)


def test_trigger_eval_runner_lints_static_boundary_fixtures():
    path = ROOT / "evals" / "trigger_eval_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert run_trigger_eval_cases(payload) == []


def test_trigger_eval_validator_rejects_non_explicit_positive_invocation(tmp_path):
    path = tmp_path / "trigger_eval_cases.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "cases": [
                    {
                        "id": "bad-positive-cached-rerender",
                        "prompt": "Rerender this cached briefing as action_items.",
                        "input": {"kind": "cached_state"},
                        "expect": {"invoke": True, "intent": "rerender"},
                    },
                    {
                        "id": "neg-ordinary-one-off-summary",
                        "prompt": "Summarize these meeting notes and extract action items.",
                        "input": {"kind": "inline_document"},
                        "expect": {"invoke": False, "boundary": "ordinary_one_off_summary"},
                    },
                    {
                        "id": "neg-live-research",
                        "prompt": "Find and analyze today's latest financial news.",
                        "input": {"kind": "no_document"},
                        "expect": {"invoke": False, "boundary": "live_research"},
                    },
                    {
                        "id": "neg-source-code-review",
                        "prompt": "Review this diff and find bugs in the implementation.",
                        "input": {"kind": "source_code"},
                        "expect": {"invoke": False, "boundary": "source_code_review"},
                    },
                    {
                        "id": "neg-debugging",
                        "prompt": "Debug this stack trace and tell me how to fix it.",
                        "input": {"kind": "stack_trace"},
                        "expect": {"invoke": False, "boundary": "debugging"},
                    },
                    {
                        "id": "neg-translation-only",
                        "prompt": "Translate this paragraph to English only.",
                        "input": {"kind": "plain_text"},
                        "expect": {"invoke": False, "boundary": "translation_only"},
                    },
                    {
                        "id": "neg-simple-qa",
                        "prompt": "Where is the cache usually stored?",
                        "input": {"kind": "no_document"},
                        "expect": {"invoke": False, "boundary": "simple_qa"},
                    },
                    {
                        "id": "neg-general-writing",
                        "prompt": "Write a polished announcement about this product launch.",
                        "input": {"kind": "plain_text"},
                        "expect": {"invoke": False, "boundary": "general_writing"},
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    _, errors = validate_trigger_eval_cases(path)

    assert any("positive trigger should explicitly invoke briefprint" in error for error in errors)
