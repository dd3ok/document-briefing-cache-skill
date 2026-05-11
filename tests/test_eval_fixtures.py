import json
from pathlib import Path


def test_eval_fixture_cases_define_cache_and_trigger_expectations():
    path = Path("evals/briefing_eval_cases.json")

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["cases"]) >= 3
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
