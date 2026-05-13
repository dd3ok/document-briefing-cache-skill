from document_briefing_cache.cli import main


def test_cli_rejects_url_input_without_fetching(capsys):
    result = main(["run", "-i", "https://example.com/report.md"])

    captured = capsys.readouterr()
    assert result == 2
    assert "URL fetching is not supported" in captured.err
    assert "local file path" in captured.err
    assert "source/url metadata" in captured.err
