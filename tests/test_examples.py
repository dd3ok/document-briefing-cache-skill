import json

from document_briefing_cache.cli import main


def test_incident_lifecycle_demo_benchmarks_reuse(tmp_path, capsys):
    cache_dir = tmp_path / "cache"

    assert main(
        [
            "benchmark",
            "--input",
            "examples/incident_lifecycle/initial.json",
            "--incremental-input",
            "examples/incident_lifecycle/update.json",
            "--cache-dir",
            str(cache_dir),
            "--fresh",
            "--mode",
            "brief",
            "--mode",
            "action_items",
            "--json",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    rows = payload["rows"]
    assert payload["scenario_count"] == 5
    assert [row["scenario"] for row in rows] == [
        "cold brief base",
        "same brief base",
        "rerender action_items base",
        "add incremental brief",
        "rerender debug combined",
    ]
    assert rows[0]["summarizer_calls"] == 2
    assert rows[0]["document_cache_hits"] == 0
    assert rows[0]["document_cache_misses"] == 2
    assert rows[1]["summarizer_calls"] == 0
    assert rows[1]["output_cache_hit"] is True
    assert rows[2]["summarizer_calls"] == 0
    assert rows[2]["document_cache_hits"] == 2
    assert rows[3]["summarizer_calls"] == 1
    assert rows[3]["document_cache_hits"] == 2
    assert rows[3]["document_cache_misses"] == 1
    assert rows[4]["summarizer_calls"] == 0
    assert rows[4]["document_cache_hits"] == 3


def test_incident_lifecycle_demo_brief_preserves_operational_nuance(tmp_path, capsys):
    assert main(
        [
            "run",
            "--input",
            "examples/incident_lifecycle/with_update.json",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--mode",
            "brief",
            "--no-output-cache",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "Status: mitigated, not resolved." in output
    assert "Metric: authorization error rate dropped to 0.7%." in output
    assert "Communication restriction: do not publish root cause externally until Legal approves." in output
