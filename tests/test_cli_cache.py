import json

from document_briefing_cache.cache import JsonFileCache
from document_briefing_cache.cli import build_run_parser, main


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


def test_cli_cache_prune_does_not_delete_signed_entries_without_secret(tmp_path, capsys):
    cache_dir = tmp_path / "cache"
    JsonFileCache(cache_dir, "document_summaries", hmac_secret="secret").set_json("signed", {"value": 1}, ttl_seconds=3600)

    assert main(["cache", "prune", "--cache-dir", str(cache_dir), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["entries_deleted"] == 0
    assert list((cache_dir / "document_summaries").glob("*.json"))


def test_cli_cache_prune_uses_hmac_secret_when_configured(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("DBC_TEST_HMAC", "secret")
    cache_dir = tmp_path / "cache"
    cache = JsonFileCache(cache_dir, "document_summaries", hmac_secret="secret")
    cache.set_json("signed", {"value": 1}, ttl_seconds=3600)
    path = cache.path_for("signed")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["expires_at"] = None
    path.write_text(json.dumps(envelope), encoding="utf-8")

    assert main(
        [
            "cache",
            "prune",
            "--cache-dir",
            str(cache_dir),
            "--layer",
            "document_summaries",
            "--cache-hmac-secret-env",
            "DBC_TEST_HMAC",
            "--json",
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["entries_deleted"] == 1
    assert list((cache_dir / "document_summaries").glob("*.json")) == []


def test_cli_run_parser_accepts_openai_llm_budget_flags():
    parser = build_run_parser()

    args = parser.parse_args(
        [
            "-i",
            "docs.json",
            "--summary-mode",
            "openai",
            "--openai-model",
            "gpt-test",
            "--llm-timeout",
            "10.5",
            "--llm-max-retries",
            "4",
            "--llm-max-input-tokens",
            "2048",
            "--llm-max-output-tokens",
            "512",
        ]
    )

    assert args.openai_model == "gpt-test"
    assert args.llm_timeout == 10.5
    assert args.llm_max_retries == 4
    assert args.llm_max_input_tokens == 2048
    assert args.llm_max_output_tokens == 512
