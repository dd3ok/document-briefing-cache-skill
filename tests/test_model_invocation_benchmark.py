from pathlib import Path

from scripts.validate_skill import validate_model_invocation_benchmark_cases, validate_model_invocation_benchmark_cases_from_payload


ROOT = Path(__file__).resolve().parents[1]


def test_model_invocation_benchmark_fixture_is_manual_and_schema_valid():
    path = ROOT / "evals" / "model_invocation_benchmark_cases.json"
    payload, errors = validate_model_invocation_benchmark_cases(path)

    assert errors == []
    assert payload["manual"] is True
    assert any(case["expected_invocation"] for case in payload["cases"])
    assert any(not case["expected_invocation"] for case in payload["cases"])
    assert all("observed_invocation" in case for case in payload["cases"])


def test_model_invocation_benchmark_requires_manual_true():
    payload, errors = validate_model_invocation_benchmark_cases(ROOT / "evals" / "model_invocation_benchmark_cases.json")
    payload["manual"] = False
    path = ROOT / "evals" / "model_invocation_benchmark_cases.json"

    errors = validate_model_invocation_benchmark_cases_from_payload(payload, path)

    assert any("manual" in error for error in errors)


def test_model_invocation_benchmark_observed_cases_require_host_model_and_date():
    payload, _errors = validate_model_invocation_benchmark_cases(ROOT / "evals" / "model_invocation_benchmark_cases.json")
    payload["cases"][0]["observed_invocation"] = True
    payload["cases"][0]["host"] = None
    payload["cases"][0]["model"] = None
    payload["cases"][0]["date"] = None
    path = ROOT / "evals" / "model_invocation_benchmark_cases.json"

    errors = validate_model_invocation_benchmark_cases_from_payload(payload, path)

    assert any("observed_invocation" in error for error in errors)
