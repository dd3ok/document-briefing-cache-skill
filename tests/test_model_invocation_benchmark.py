from pathlib import Path

from scripts.validate_skill import validate_model_invocation_benchmark_cases


ROOT = Path(__file__).resolve().parents[1]


def test_model_invocation_benchmark_fixture_is_manual_and_schema_valid():
    path = ROOT / "evals" / "model_invocation_benchmark_cases.json"
    payload, errors = validate_model_invocation_benchmark_cases(path)

    assert errors == []
    assert payload["manual"] is True
    assert any(case["expected_invocation"] for case in payload["cases"])
    assert any(not case["expected_invocation"] for case in payload["cases"])
    assert all("observed_invocation" in case for case in payload["cases"])
