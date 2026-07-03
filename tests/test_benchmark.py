import json

import pytest

from document_briefing_cache.benchmark import BenchmarkScenario, build_standard_scenarios, run_benchmark
from document_briefing_cache.cli import main
from document_briefing_cache.models import DocumentInput
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


def sample_docs():
    return [
        DocumentInput(document_id="ticket-1", title="Ticket", text="Action: Support should reply by 2026-05-10."),
        DocumentInput(document_id="incident-1", title="Incident", text="Risk: checkout conversion may drop. Metric: error rate 2.4%."),
    ]


def update_docs():
    return [
        DocumentInput(document_id="update-1", title="Update", text="Action: Backend should update the runbook by 2026-05-12."),
    ]


def repeated_operational_doc(items=10):
    return DocumentInput(
        document_id="ops-long",
        title="Long Ops Log",
        text="\n".join(
            f"Decision: approve rollout gate {i}. "
            f"Action: team-{i} should update runbook RB-{i}. "
            f"Risk: service svc-{i} may fail. "
            f"Metric: latency {100 + i} ms."
            for i in range(items)
        ),
    )


def test_run_benchmark_reports_cache_token_savings(tmp_path):
    scenarios = build_standard_scenarios(
        base_documents=sample_docs(),
        incremental_documents=update_docs(),
        modes=["brief", "digest", "action_items"],
    )

    report = run_benchmark(
        scenarios,
        cache_dir=tmp_path / "cache",
        summarizer=RuleBasedExtractiveSummarizer(),
    )

    rows = report["rows"]
    assert [row["scenario"] for row in rows] == [
        "cold brief base",
        "same brief base",
        "rerender digest base",
        "rerender action_items base",
        "add incremental brief",
        "rerender debug combined",
    ]
    assert rows[0]["document_cache_misses"] == 2
    assert rows[0]["summarizer_calls"] == 2
    assert rows[1]["output_cache_hit"] is True
    assert rows[1]["summarizer_calls"] == 0
    assert rows[1]["quality"]["evaluated"] is False
    assert report["quality_unevaluated_rows"] == 1
    assert rows[2]["document_cache_hits"] == 2
    assert rows[2]["summarizer_calls"] == 0
    assert rows[4]["document_cache_hits"] == 2
    assert rows[4]["document_cache_misses"] == 1
    assert rows[4]["summarizer_calls"] == 1
    assert report["cacheaware_cache_miss_only_input_tokens_est"] < report["naive_resummarize_every_run_input_tokens_est"]
    assert report["estimated_savings_percent"] > 0


def test_run_benchmark_reports_quality_coverage_warnings(tmp_path):
    report = run_benchmark(
        [BenchmarkScenario(name="cold debug long", documents=[repeated_operational_doc()], mode="debug")],
        cache_dir=tmp_path / "cache",
        summarizer=RuleBasedExtractiveSummarizer(),
    )

    row_quality = report["rows"][0]["quality"]

    assert row_quality["source_candidates"]["actions"] == 10
    assert row_quality["extracted"]["actions"] == 8
    assert row_quality["coverage_percent"]["actions"] == 80.0
    assert row_quality["source_candidates"]["decisions"] == 10
    assert row_quality["extracted"]["decisions"] == 8
    assert row_quality["source_candidates"]["risks"] == 10
    assert row_quality["extracted"]["risks"] == 8
    assert row_quality["warnings"]
    assert report["quality_warning_rows"] == 1


def test_run_benchmark_fresh_cache_resets_prior_results(tmp_path):
    scenarios = build_standard_scenarios(
        base_documents=sample_docs(),
        modes=["brief", "digest"],
    )
    cache_dir = tmp_path / "cache"

    first = run_benchmark(scenarios, cache_dir=cache_dir, summarizer=RuleBasedExtractiveSummarizer())
    warm = run_benchmark(scenarios, cache_dir=cache_dir, summarizer=RuleBasedExtractiveSummarizer())
    fresh = run_benchmark(scenarios, cache_dir=cache_dir, summarizer=RuleBasedExtractiveSummarizer(), fresh_cache=True)

    assert first["rows"][0]["summarizer_calls"] == 2
    assert warm["rows"][0]["summarizer_calls"] == 0
    assert warm["rows"][0]["output_cache_hit"] is True
    assert fresh["rows"][0]["summarizer_calls"] == 2
    assert fresh["rows"][0]["output_cache_hit"] is False


def test_run_benchmark_fresh_cache_only_clears_cache_namespaces(tmp_path):
    cache_dir = tmp_path / "workspace"
    cache_dir.mkdir()
    marker = cache_dir / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    (cache_dir / "document_summaries").mkdir()
    stale = cache_dir / "document_summaries" / "stale.json"
    stale.write_text("{}", encoding="utf-8")

    run_benchmark(
        [BenchmarkScenario(name="cold brief", documents=sample_docs(), mode="brief")],
        cache_dir=cache_dir,
        summarizer=RuleBasedExtractiveSummarizer(),
        fresh_cache=True,
    )

    assert marker.read_text(encoding="utf-8") == "keep"
    assert not stale.exists()


def test_run_benchmark_fresh_cache_unlinks_namespace_symlink(tmp_path):
    cache_dir = tmp_path / "workspace"
    cache_dir.mkdir()
    target_dir = tmp_path / "outside-cache"
    target_dir.mkdir()
    protected = target_dir / "protected.txt"
    protected.write_text("keep", encoding="utf-8")
    namespace_link = cache_dir / "document_summaries"
    try:
        namespace_link.symlink_to(target_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    run_benchmark(
        [BenchmarkScenario(name="cold brief", documents=sample_docs(), mode="brief")],
        cache_dir=cache_dir,
        summarizer=RuleBasedExtractiveSummarizer(),
        fresh_cache=True,
    )

    assert namespace_link.is_dir()
    assert not namespace_link.is_symlink()
    assert protected.read_text(encoding="utf-8") == "keep"


def test_run_benchmark_fresh_cache_rejects_file_path(tmp_path):
    cache_file = tmp_path / "cache-file"
    cache_file.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="Benchmark cache path must be a directory"):
        run_benchmark(
            [BenchmarkScenario(name="cold brief", documents=sample_docs(), mode="brief")],
            cache_dir=cache_file,
            summarizer=RuleBasedExtractiveSummarizer(),
            fresh_cache=True,
        )

    assert cache_file.read_text(encoding="utf-8") == "not a directory"


def test_cli_benchmark_outputs_json(tmp_path, capsys):
    base_path = tmp_path / "base.json"
    update_path = tmp_path / "update.json"
    base_path.write_text(
        json.dumps({"documents": [{"id": "ticket-1", "title": "Ticket", "content": "Action: Support should reply."}]}),
        encoding="utf-8",
    )
    update_path.write_text(
        json.dumps({"documents": [{"id": "update-1", "title": "Update", "content": "Risk: rollout may slip."}]}),
        encoding="utf-8",
    )

    assert main(
        [
            "benchmark",
            "--input",
            str(base_path),
            "--incremental-input",
            str(update_path),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--mode",
            "brief",
            "--mode",
            "digest",
            "--json",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["scenario_count"] == 5
    assert payload["rows"][0]["scenario"] == "cold brief base"
    assert payload["rows"][0]["summarizer_calls"] == 1
    assert payload["rows"][2]["scenario"] == "rerender digest base"
    assert payload["rows"][2]["summarizer_calls"] == 0
    assert payload["estimated_tokens_saved"] > 0
    assert "quality" in payload["rows"][0]


def test_cli_benchmark_text_reports_quality_warnings(tmp_path, capsys):
    base_path = tmp_path / "base.json"
    base_path.write_text(
        json.dumps({"documents": [{"id": "ops-long", "title": "Long Ops Log", "content": repeated_operational_doc().text}]}),
        encoding="utf-8",
    )

    assert main(
        [
            "benchmark",
            "--input",
            str(base_path),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--mode",
            "debug",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "quality_warning_rows: 1" in output
    assert "quality_warnings=3" in output
    assert "quality_unevaluated_rows: 1" in output


def test_cli_benchmark_can_split_input_sections(tmp_path, capsys):
    base_path = tmp_path / "ops.md"
    base_path.write_text(
        "# One\nAction: owner should update runbook.\n\n# Two\nRisk: rollout may slip.",
        encoding="utf-8",
    )

    assert main(
        [
            "benchmark",
            "--input",
            str(base_path),
            "--split-input-sections",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--mode",
            "brief",
            "--json",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["rows"][0]["documents"] == 2


def test_cli_benchmark_can_split_incident_records(tmp_path, capsys):
    base_path = tmp_path / "incident-base.md"
    base_path.write_text(
        "Incident ID: INC-1\n"
        "Status: open. Risk: checkout errors may continue.\n\n"
        "Incident Update: 2026-07-03 15:30 KST\n"
        "Action: SRE should confirm error rate by 16:00 KST.",
        encoding="utf-8",
    )
    update_path = tmp_path / "incident-update.md"
    update_path.write_text(
        "Incident ID: INC-1\n"
        "Incident Update: 2026-07-03 16:00 KST\n"
        "Decision: keep monitoring for 30 minutes.",
        encoding="utf-8",
    )

    assert main(
        [
            "benchmark",
            "--input",
            str(base_path),
            "--incremental-input",
            str(update_path),
            "--split-records",
            "incident",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--mode",
            "brief",
            "--json",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["rows"][0]["documents"] == 2
    assert payload["rows"][2]["scenario"] == "add incremental brief"
    assert payload["rows"][2]["document_cache_hits"] == 2
    assert payload["rows"][2]["document_cache_misses"] == 1
    assert payload["rows"][2]["summarizer_calls"] == 1


def test_cli_run_uses_shared_document_loader(tmp_path, capsys):
    input_path = tmp_path / "ticket.json"
    input_path.write_text(
        json.dumps({"documents": [{"id": "ticket-1", "title": "Ticket", "content": "Action: Support should reply."}]}),
        encoding="utf-8",
    )

    assert main(["--input", str(input_path), "--mode", "brief", "--cache-dir", str(tmp_path / "cache")]) == 0

    assert "Support should reply" in capsys.readouterr().out
