from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest


def test_installed_package_renders_packaged_templates(tmp_path):
    if os.environ.get("DBC_RUN_INSTALLED_SMOKE") != "1":
        pytest.skip("set DBC_RUN_INSTALLED_SMOKE=1 to run installed package smoke")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = textwrap.dedent(
        """
        from document_briefing_cache.models import DocumentInput
        from document_briefing_cache.pipeline import BriefingPipeline

        docs = [
            DocumentInput(
                document_id="dist",
                title="Distribution",
                text="Action: Release worker should package templates.",
            )
        ]
        result = BriefingPipeline(cache_dir="cache").run(docs, mode="brief", use_output_cache=False)
        assert "문서 브리핑" in result.output
        assert "Distribution" in result.output
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
