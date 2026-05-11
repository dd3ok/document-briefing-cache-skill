import json

from document_briefing_cache.cli import main


def test_cli_cache_stats_prune_and_clear(tmp_path, capsys):
    input_path = tmp_path / "docs.json"
    input_path.write_text(
        json.dumps({"documents": [{"id": "x", "title": "X", "content": "Decision: proceed."}]}),
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"

    assert main(["run", "-i", str(input_path), "--cache-dir", str(cache_dir), "--show-stats"]) == 0
    capsys.readouterr()

    assert main(["cache", "stats", "--cache-dir", str(cache_dir), "--json"]) == 0
    stats_output = capsys.readouterr().out
    assert "document_summaries" in stats_output

    assert main(["cache", "prune", "--cache-dir", str(cache_dir), "--older-than", "0s", "--dry-run", "--json"]) == 0
    prune_output = capsys.readouterr().out
    assert "entries_deleted" in prune_output

    assert main(["cache", "clear", "--cache-dir", str(cache_dir), "--layer", "all", "--yes", "--json"]) == 0
    clear_output = capsys.readouterr().out
    assert "entries_deleted" in clear_output


def test_cli_run_supports_redaction_and_hmac_flags(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("DBC_TEST_HMAC", "secret")
    input_path = tmp_path / "sensitive.json"
    input_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "ticket-privacy",
                        "title": "Customer follow-up",
                        "content": "Action: Support should email alice@example.com and call 010-1234-5678 by 2026-05-12.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"

    assert main(
        [
            "run",
            "-i",
            str(input_path),
            "--cache-dir",
            str(cache_dir),
            "--redact-pii",
            "--cache-hmac-secret-env",
            "DBC_TEST_HMAC",
            "--show-stats",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "alice@example.com" not in output
    assert "010-1234-5678" not in output
    assert "REDACTED:email" in output
    assert "REDACTED:phone" in output

    cache_text = "\n".join(path.read_text(encoding="utf-8") for path in cache_dir.rglob("*.json"))
    assert "payload_hmac_sha256" in cache_text
    assert "alice@example.com" not in cache_text
    assert "010-1234-5678" not in cache_text
