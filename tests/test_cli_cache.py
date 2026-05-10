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
