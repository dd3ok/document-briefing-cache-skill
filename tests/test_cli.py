import json
import re

from document_briefing_cache.cli import main


def test_cli_run_explain_cache_outputs_document_events(tmp_path, capsys):
    input_path = tmp_path / "doc.json"
    input_path.write_text(
        json.dumps({"documents": [{"id": "doc-1", "title": "Doc", "content": "Action: owner should reply."}]}),
        encoding="utf-8",
    )

    assert main(
        [
            "--input",
            str(input_path),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--show-stats",
            "--explain-cache",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "## Cache explanation" in output
    assert re.search(r"\| doc-1 \| [0-9a-f]{12} \| miss \| miss_new_fingerprint \|", output)
    assert "miss_new_fingerprint" in output
    assert "Output cache:" in output


def test_cli_run_explain_cache_outputs_output_hit_reason(tmp_path, capsys):
    input_path = tmp_path / "doc.json"
    input_path.write_text(
        json.dumps({"documents": [{"id": "doc-1", "title": "Doc", "content": "Action: owner should reply."}]}),
        encoding="utf-8",
    )
    args = [
        "--input",
        str(input_path),
        "--cache-dir",
        str(tmp_path / "cache"),
        "--explain-cache",
    ]

    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 0

    output = capsys.readouterr().out
    assert "| n/a | n/a | n/a | output cache hit before document cache lookup |" in output
    assert "- result: hit" in output
    assert "- reason: output_hit_same_render_key" in output


def test_cli_sensitive_alias_uses_ephemeral_redacted_no_output_cache(tmp_path, capsys):
    input_path = tmp_path / "private.json"
    input_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "alice@example.com",
                        "title": "Private follow-up",
                        "source": "mailto:alice@example.com",
                        "content": "Action: Support should email alice@example.com by 2026-07-04.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "--input",
            str(input_path),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--sensitive",
            "--show-stats",
            "--explain-cache",
        ]
    ) == 0

    output = capsys.readouterr().out
    stats_text = output.split("--- stats ---", 1)[1].split("\n## Cache explanation", 1)[0]
    stats = json.loads(stats_text)
    assert "alice@example.com" not in output
    assert "mailto:alice@example.com" not in output
    assert "REDACTED:email" in output
    assert stats["sensitive_mode"] is True
    assert stats["cache_policy"] == "ephemeral"
    assert stats["pii_redactions"] >= 1
    assert stats["delete_on_exit_applied"] is True
    assert stats["output_cache_event"]["status"] == "disabled"
    assert stats["output_cache_event"]["reason"] == "output_disabled"
    assert not list((tmp_path / "cache" / "document_summaries").glob("*.json"))
    assert not list((tmp_path / "cache" / "rendered_outputs").glob("*.json"))


def test_cli_manual_sensitive_equivalent_flags_do_not_set_sensitive_alias_marker(tmp_path, capsys):
    input_path = tmp_path / "private.json"
    input_path.write_text(
        json.dumps({"documents": [{"id": "private-1", "title": "Private follow-up", "content": "Action: Support should email alice@example.com."}]}),
        encoding="utf-8",
    )

    assert main(
        [
            "--input",
            str(input_path),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--cache-policy",
            "ephemeral",
            "--no-output-cache",
            "--redact-pii",
            "--delete-on-exit",
            "created",
            "--show-stats",
        ]
    ) == 0

    output = capsys.readouterr().out
    stats = json.loads(output.split("--- stats ---", 1)[1])
    assert stats["sensitive_mode"] is False
    assert stats["cache_policy"] == "ephemeral"
    assert stats["pii_redactions"] >= 1
    assert stats["delete_on_exit_applied"] is True
