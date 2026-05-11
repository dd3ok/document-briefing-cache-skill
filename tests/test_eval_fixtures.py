import json
from copy import deepcopy
from pathlib import Path

from scripts.validate_skill import run_eval_cases


def test_eval_fixture_cases_define_cache_and_trigger_expectations():
    path = Path("evals/briefing_eval_cases.json")

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["cases"]) >= 5
    has_state_expectation = False
    for case in payload["cases"]:
        assert case["id"]
        assert "documents" in case["input"]
        assert case["runs"]
        for run in case["runs"]:
            assert run["id"]
            assert run["prompt"]
            assert run["mode"] in {"brief", "executive", "action_items", "digest", "debug"}
            assert "summarizer_calls" in run["expect"]["stats"]
            assert "document_cache_hits" in run["expect"]["stats"]
            if "summary_state" in run["expect"]:
                has_state_expectation = True
                assert isinstance(run["expect"]["summary_state"], dict)
    assert has_state_expectation


def test_eval_runner_fails_when_summary_state_needle_is_missing():
    path = Path("evals/briefing_eval_cases.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = {"cases": [deepcopy(payload["cases"][0])]}
    payload["cases"][0]["runs"][0]["expect"]["summary_state"]["actions_contains"] = ["IMPOSSIBLE-ACTION-VALUE"]

    errors = run_eval_cases(payload)

    assert errors
    assert "summary_state.actions_contains" in errors[0]


def test_eval_runner_fails_on_unsupported_summary_state_expectation():
    path = Path("evals/briefing_eval_cases.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = {"cases": [deepcopy(payload["cases"][0])]}
    payload["cases"][0]["runs"][0]["expect"]["summary_state"] = {"unsupported_contains": ["PAY-482"]}

    errors = run_eval_cases(payload)

    assert errors
    assert "unsupported summary_state expectation" in errors[0]
