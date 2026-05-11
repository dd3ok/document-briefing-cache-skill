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
    assert any(case["expect"].get("boundary") == "source_code_review" for case in negatives)
    assert any(case["expect"].get("boundary") == "translation_only" for case in negatives)
    assert any(case["expect"].get("intent") == "summarize_review_comments" for case in positives)
    assert any(case["prompt"] == "오늘 최신 금융 뉴스를 찾아서 분석해줘." for case in cases)


def test_trigger_eval_runner_detects_expected_invocation_decisions():
    path = ROOT / "evals" / "trigger_eval_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert run_trigger_eval_cases(payload) == []
