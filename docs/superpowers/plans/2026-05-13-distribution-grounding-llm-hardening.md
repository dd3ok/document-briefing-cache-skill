# Distribution Grounding LLM Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository from a working source-tree demo into a distributable, honest, better-grounded document briefing skill with a clearer LLM production path.

**Architecture:** Fix packaging first so runtime templates are package resources, then update documentation and input boundaries, then strengthen evidence validation, then introduce schema v1.1 evidence fields, and only then harden the OpenAI adapter. This order keeps each step independently testable and avoids mixing schema churn with packaging churn.

**Tech Stack:** Python 3.10+, setuptools, Jinja2, Pydantic v2, pytest, GitHub Actions, optional OpenAI Responses API adapter.

**Execution status:** Implemented on branch `codex/distribution-grounding-llm-hardening` on 2026-05-13. Subagent spec and quality reviews were used task-by-task; final verification is recorded in `VALIDATION.md`.

---

## Subagent Dispatch Map

Use fresh workers per task group. Workers are not alone in the codebase; they must not revert edits made by other workers and should adjust their work to fit already-merged changes.

- **Worker A: Packaging and CI** owns Tasks 1-3.
- **Worker B: Input scope and privacy docs** owns Tasks 4-7.
- **Worker C: Evidence grounding** owns Tasks 8-9.
- **Worker D: LLM production path** owns Task 10.
- **Coordinator** reviews after each task, runs the listed verification command, and only dispatches the next dependent task after the current task is green.

Do not run Tasks 8-10 before Tasks 1-7 are merged. Do not run Task 10 before Task 9 lands, because the LLM adapter should target the current schema.

---

### Task 1: Package Templates As Runtime Resources

**Files:**
- Move: `templates/brief.md.j2` -> `src/document_briefing_cache/templates/brief.md.j2`
- Move: `templates/executive.md.j2` -> `src/document_briefing_cache/templates/executive.md.j2`
- Move: `templates/action_items.md.j2` -> `src/document_briefing_cache/templates/action_items.md.j2`
- Move: `templates/digest.md.j2` -> `src/document_briefing_cache/templates/digest.md.j2`
- Move: `templates/debug.md.j2` -> `src/document_briefing_cache/templates/debug.md.j2`
- Modify: `src/document_briefing_cache/render.py`
- Modify: `pyproject.toml`
- Create: `MANIFEST.in`
- Create: `tests/test_packaging.py`

- [ ] **Step 1: Write failing packaging tests**

Create `tests/test_packaging.py`:

```python
from importlib import resources

from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline


def test_templates_are_packaged_resources():
    template_root = resources.files("document_briefing_cache").joinpath("templates")
    names = {path.name for path in template_root.iterdir()}

    assert {
        "brief.md.j2",
        "executive.md.j2",
        "action_items.md.j2",
        "digest.md.j2",
        "debug.md.j2",
    }.issubset(names)


def test_default_renderer_uses_packaged_templates(tmp_path):
    docs = [
        DocumentInput(
            document_id="pkg",
            title="Packaging",
            text="Action: Release worker should package templates.",
        )
    ]

    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="brief", use_output_cache=False)

    assert "문서 브리핑" in result.output
    assert "Packaging" in result.output
```

- [ ] **Step 2: Run RED**

Run:

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_packaging.py -q
```

Expected: FAIL because `document_briefing_cache/templates` does not exist yet.

- [ ] **Step 3: Move template files**

Create `src/document_briefing_cache/templates/`, move all five root templates into it, and remove the now-empty root `templates/` directory.

- [ ] **Step 4: Load templates from the installed package**

Modify `src/document_briefing_cache/render.py` so default rendering uses Jinja `PackageLoader`, while explicit `template_dir` keeps using `FileSystemLoader`.

Target shape:

```python
from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined


DEFAULT_TEMPLATE_PACKAGE = "document_briefing_cache"
DEFAULT_TEMPLATE_PATH = "templates"
TEMPLATE_VERSION = "templates-v0.2.0"


def _build_environment(template_dir: str | Path | None) -> Environment:
    loader = (
        FileSystemLoader(str(Path(template_dir)))
        if template_dir is not None
        else PackageLoader(DEFAULT_TEMPLATE_PACKAGE, DEFAULT_TEMPLATE_PATH)
    )
    env = Environment(
        loader=loader,
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["md"] = markdown_inline_escape
    return env
```

In `render_briefing`, use `env.list_templates(filter_func=lambda name: name.endswith(".md.j2"))` to compute available modes instead of `Path(template_dir).glob("*.md.j2")`.

- [ ] **Step 5: Add package-data settings**

Modify `pyproject.toml`:

```toml
[tool.setuptools.package-data]
document_briefing_cache = ["templates/*.md.j2"]
```

Add `build>=1.2.0` to `[project.optional-dependencies].dev`.

- [ ] **Step 6: Add source distribution manifest**

Create `MANIFEST.in`:

```text
recursive-include src/document_briefing_cache/templates *.md.j2
include README.md LICENSE AGENTS.md SKILL.md VALIDATION.md
recursive-include examples *.json
recursive-include evals *.json
recursive-include references *.md
recursive-include agents *.yaml
recursive-include docs *.md
```

- [ ] **Step 7: Run GREEN**

Run:

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_packaging.py tests/test_rendering.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml MANIFEST.in src/document_briefing_cache/render.py src/document_briefing_cache/templates tests/test_packaging.py
git add -u templates
git commit -m "fix: package briefing templates"
```

---

### Task 2: Update Validation And Documentation For Template Move

**Files:**
- Modify: `scripts/validate_skill.py`
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `VALIDATION.md`

- [ ] **Step 1: Update validation script paths**

In `scripts/validate_skill.py`, replace required root template paths with package paths:

```python
"src/document_briefing_cache/templates/brief.md.j2",
"src/document_briefing_cache/templates/executive.md.j2",
"src/document_briefing_cache/templates/action_items.md.j2",
"src/document_briefing_cache/templates/digest.md.j2",
"src/document_briefing_cache/templates/debug.md.j2",
```

Set:

```python
template_dir = ROOT / "src" / "document_briefing_cache" / "templates"
```

- [ ] **Step 2: Update docs**

Update the repository layout in `README.md` so templates appear under `src/document_briefing_cache/templates/`.

Update the progressive disclosure line in `SKILL.md` from `render.py and templates/*.md.j2` to `render.py and src/document_briefing_cache/templates/*.md.j2`.

Update `VALIDATION.md` to add the future distribution smoke commands from Task 3.

- [ ] **Step 3: Verify**

Run:

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_docs.py tests/test_skill_metadata.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/validate_skill.py
```

Expected: tests pass and validation prints a line starting with `OK: briefprint skill repository validated`.

- [ ] **Step 4: Commit**

```bash
git add scripts/validate_skill.py README.md SKILL.md VALIDATION.md
git commit -m "docs: align validation with packaged templates"
```

---

### Task 3: Add Distribution Smoke And CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `tests/test_distribution_smoke.py`

- [ ] **Step 1: Add installed-package smoke test helper**

Create `tests/test_distribution_smoke.py` with a small subprocess-based smoke that can be reused locally after installing a wheel. Keep it skipped unless `DBC_RUN_INSTALLED_SMOKE=1` is set, so normal source-tree tests stay fast.

```python
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.getenv("DBC_RUN_INSTALLED_SMOKE") != "1", reason="installed package smoke is opt-in")
def test_installed_package_renders_without_repo_templates(tmp_path):
    script = (
        "from document_briefing_cache.models import DocumentInput\n"
        "from document_briefing_cache.pipeline import BriefingPipeline\n"
        f"r=BriefingPipeline(cache_dir={str(tmp_path)!r}).run("
        "[DocumentInput(document_id='x', title='X', text='Action: package smoke.')], "
        "mode='brief', use_output_cache=False)\n"
        "assert '문서 브리핑' in r.output\n"
    )

    subprocess.run([sys.executable, "-c", script], check=True, cwd=str(tmp_path))
```

- [ ] **Step 2: Create GitHub Actions workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e ".[dev]"
      - run: TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
      - run: PYTHONDONTWRITEBYTECODE=1 python scripts/validate_skill.py --run-evals

  dist-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip build
      - run: python -m build
      - run: python -m venv /tmp/dbc-wheel
      - run: /tmp/dbc-wheel/bin/python -m pip install dist/*.whl
      - run: |
          cd /tmp
          /tmp/dbc-wheel/bin/python - <<'PY'
          from document_briefing_cache.models import DocumentInput
          from document_briefing_cache.pipeline import BriefingPipeline
          result = BriefingPipeline(cache_dir="/tmp/dbc-wheel-cache").run(
              [DocumentInput(document_id="wheel", title="Wheel", text="Action: smoke wheel.")],
              mode="brief",
              use_output_cache=False,
          )
          assert "문서 브리핑" in result.output
          PY
      - run: python -m venv /tmp/dbc-sdist
      - run: /tmp/dbc-sdist/bin/python -m pip install dist/*.tar.gz
      - run: |
          cd /tmp
          /tmp/dbc-sdist/bin/python - <<'PY'
          from document_briefing_cache.models import DocumentInput
          from document_briefing_cache.pipeline import BriefingPipeline
          result = BriefingPipeline(cache_dir="/tmp/dbc-sdist-cache").run(
              [DocumentInput(document_id="sdist", title="Sdist", text="Action: smoke sdist.")],
              mode="brief",
              use_output_cache=False,
          )
          assert "문서 브리핑" in result.output
          PY
```

- [ ] **Step 3: Verify locally**

Run:

```bash
python3 -m pip install -e ".[dev]"
python3 -m build
python3 -m venv /tmp/dbc-wheel
/tmp/dbc-wheel/bin/python -m pip install dist/*.whl
cd /tmp && /tmp/dbc-wheel/bin/python -c "from document_briefing_cache.models import DocumentInput; from document_briefing_cache.pipeline import BriefingPipeline; r=BriefingPipeline(cache_dir='/tmp/dbc-cache').run([DocumentInput(document_id='x', title='X', text='Action: ship package templates.')], mode='brief', use_output_cache=False); assert '문서 브리핑' in r.output"
```

Expected: all commands succeed.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml tests/test_distribution_smoke.py
git commit -m "ci: add distribution smoke tests"
```

---

### Task 4: Clarify Local Input And URL Metadata Boundary

**Files:**
- Modify: `tests/test_docs.py`
- Modify: `README.md`
- Modify: `SKILL.md`

- [ ] **Step 1: Add failing docs test**

Append to `tests/test_docs.py`:

```python
def test_readme_documents_local_path_and_url_metadata_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "--input" in readme
    assert "local file path" in readme
    assert "does not fetch URLs" in readme
    assert "URL-bearing metadata" in readme
    assert "URL-bearing metadata" in skill
    assert "file paths, URLs" not in skill.split("---", 2)[1]
```

- [ ] **Step 2: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_docs.py::test_readme_documents_local_path_and_url_metadata_boundary -q
```

Expected: FAIL until docs are updated.

- [ ] **Step 3: Update docs**

In `README.md`, add an `Input scope` section after the install or run section:

```markdown
## Input scope

The CLI `--input` option currently accepts local file paths. It does not fetch `http://` or `https://` URLs.

URL-bearing metadata inside JSON, XML, HTML, or `DocumentInput.source` is preserved as source/reference metadata for evidence and rendering. To summarize remote content, fetch it outside this tool and pass the saved local file or normalized payload.
```

In `SKILL.md` frontmatter, change the description phrase from `file paths, URLs, JSON/XML/API payloads` to `local file paths, URL-bearing metadata/source references, JSON/XML/API payloads`.

- [ ] **Step 4: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_docs.py tests/test_skill_metadata.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md SKILL.md tests/test_docs.py
git commit -m "docs: clarify URL input boundary"
```

---

### Task 5: Reject URL CLI Inputs Without Fetching

**Files:**
- Create: `tests/test_cli_inputs.py`
- Modify: `src/document_briefing_cache/cli.py`

- [ ] **Step 1: Add failing CLI test**

Create `tests/test_cli_inputs.py`:

```python
from document_briefing_cache.cli import main


def test_cli_rejects_url_input_without_fetching(capsys):
    result = main(["run", "-i", "https://example.com/report.md"])

    captured = capsys.readouterr()
    assert result == 2
    assert "URL fetching is not supported" in captured.err
    assert "local file path" in captured.err
    assert "source/url metadata" in captured.err
```

- [ ] **Step 2: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_cli_inputs.py -q
```

Expected: FAIL because the CLI currently tries to read the URL as a path.

- [ ] **Step 3: Implement explicit rejection**

Modify `src/document_briefing_cache/cli.py`:

```python
def is_http_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")
```

At the beginning of `run_with_args`:

```python
for input_path in args.input:
    if is_http_url(input_path):
        sys.stderr.write(
            "URL fetching is not supported by --input. "
            "Pass a local file path, or include source/url metadata inside a JSON/XML payload.\n"
        )
        return 2
```

Then keep the existing document loading loop.

- [ ] **Step 4: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_cli_inputs.py tests/test_cli_cache.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/document_briefing_cache/cli.py tests/test_cli_inputs.py
git commit -m "fix: reject URL inputs explicitly"
```

---

### Task 6: Preserve Normalization Uncertainty

**Files:**
- Modify: `tests/test_normalize.py`
- Modify: `tests/test_pipeline_cache.py`
- Modify: `src/document_briefing_cache/normalize.py`
- Modify: `src/document_briefing_cache/pipeline.py`
- Modify: `references/schema.md`

- [ ] **Step 1: Add failing normalize tests**

Append to `tests/test_normalize.py`:

```python
def test_url_fields_are_preserved_as_source_metadata_without_fetching():
    docs = normalize_payload(
        {"documents": [{"id": "u1", "title": "Remote Copy", "url": "https://example.com/report", "content": "Decision: keep local copy."}]}
    )

    assert docs[0].source == "https://example.com/report"
    assert docs[0].metadata["url"] == "https://example.com/report"
    assert "keep local copy" in docs[0].text


def test_unknown_payload_records_normalization_unknowns_metadata():
    docs = normalize_payload(object(), source="opaque")

    assert docs[0].source == "opaque"
    assert docs[0].metadata["normalization_unknowns"]
    assert "Unsupported payload type" in docs[0].metadata["normalization_unknowns"][0]
```

- [ ] **Step 2: Add failing pipeline propagation test**

Append to `tests/test_pipeline_cache.py`:

```python
def test_pipeline_copies_normalization_unknowns_to_summary_unknowns(tmp_path):
    docs = [
        DocumentInput(
            document_id="opaque",
            title="Opaque",
            text="Some fallback text.",
            metadata={"normalization_unknowns": ["Unsupported payload type: object"]},
        )
    ]

    result = BriefingPipeline(cache_dir=tmp_path).run(docs, mode="debug", use_output_cache=False)

    assert "Unsupported payload type: object" in result.summaries[0].unknowns
```

- [ ] **Step 3: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_normalize.py tests/test_pipeline_cache.py -q
```

Expected: FAIL until metadata and propagation are implemented.

- [ ] **Step 4: Preserve URL metadata in JSON mappings**

In `src/document_briefing_cache/normalize.py`, when building `metadata` in `document_from_mapping`, keep non-text fields including `url`.

Target:

```python
metadata={k: v for k, v in item.items() if k not in set(TEXT_KEYS)}
```

This already preserves `url`; keep the test to lock behavior.

- [ ] **Step 5: Add normalization unknown helper**

Add:

```python
NORMALIZATION_UNKNOWNS_KEY = "normalization_unknowns"


def normalization_unknown(message: str) -> dict[str, list[str]]:
    return {NORMALIZATION_UNKNOWNS_KEY: [message]}
```

In the fallback branch of `normalize_payload`, return:

```python
return [
    DocumentInput(
        source=source,
        content_format=ContentFormat.text,
        text=str(payload),
        doc_type=DocumentType.unknown,
        metadata=normalization_unknown(f"Unsupported payload type: {type(payload).__name__}"),
    )
]
```

- [ ] **Step 6: Propagate normalization unknowns into summaries**

In `src/document_briefing_cache/pipeline.py`, after `summary = self.summarizer.summarize(summary_document, sections, fingerprint)` and before evidence validation:

```python
normalization_unknowns = summary_document.metadata.get("normalization_unknowns", [])
if isinstance(normalization_unknowns, list):
    for unknown in normalization_unknowns:
        if isinstance(unknown, str) and unknown not in summary.unknowns:
            summary.unknowns.append(unknown)
```

- [ ] **Step 7: Document the metadata convention**

In `references/schema.md`, add a short section:

```markdown
## Normalization Unknowns

When an input is accepted through a fallback path, normalizers should preserve the text representation and add `DocumentInput.metadata.normalization_unknowns` as a list of human-readable uncertainty strings. The pipeline copies these values into `DocumentSummaryState.unknowns` on cache misses so rendered output can expose normalization caveats.
```

- [ ] **Step 8: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_normalize.py tests/test_pipeline_cache.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/document_briefing_cache/normalize.py src/document_briefing_cache/pipeline.py tests/test_normalize.py tests/test_pipeline_cache.py references/schema.md
git commit -m "feat: preserve normalization unknowns"
```

---

### Task 7: Tighten Privacy And Sensitive Document Guidance

**Files:**
- Modify: `tests/test_docs.py`
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `references/best-practices.md`

- [ ] **Step 1: Add failing documentation test**

Append to `tests/test_docs.py`:

```python
def test_readme_documents_redaction_scope_and_security_limits():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    best_practices = (ROOT / "references" / "best-practices.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, skill, best_practices])

    assert "basic-contact-v1" in combined
    assert "email" in combined
    assert "Korean mobile" in combined
    assert "US phone" in combined
    assert "not a complete PII detector" in combined
    assert "--cache-policy ephemeral" in combined
    assert "--no-output-cache" in combined
    assert "encrypted storage" in combined
    assert "tmpfs" in combined
    assert "tamper detection only" in combined
    assert "not encryption" in combined
```

- [ ] **Step 2: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_docs.py::test_readme_documents_redaction_scope_and_security_limits -q
```

Expected: FAIL until docs are precise enough.

- [ ] **Step 3: Update README sensitive docs section**

Add language near the cache lifecycle/privacy note:

```markdown
For sensitive documents, the safe default is no persistent cache:

```bash
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --cache-policy ephemeral \
  --no-output-cache \
  --redact-pii
```

The built-in `basic-contact-v1` profile covers common email addresses, Korean mobile numbers, and US phone numbers. It is not a complete PII detector for names, addresses, national IDs, account numbers, cards, API keys, or access tokens.

HMAC signing is tamper detection only, not encryption. Use encrypted storage, tmpfs, or another encrypted backend when cache contents need confidentiality.
```

- [ ] **Step 4: Align SKILL and best practices**

Use the same wording in `SKILL.md` safety defaults and `references/best-practices.md`.

- [ ] **Step 5: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_docs.py tests/test_privacy.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md SKILL.md references/best-practices.md tests/test_docs.py
git commit -m "docs: tighten privacy guidance"
```

---

### Task 8: Require Evidence On Existing Source-Backed Items

**Files:**
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_pipeline_cache.py`
- Modify: `src/document_briefing_cache/evidence.py`
- Modify: `src/document_briefing_cache/summarizers.py`

- [ ] **Step 1: Add failing evidence tests**

Append to `tests/test_evidence.py`:

```python
from document_briefing_cache.models import Decision, KeyPoint


def test_validate_summary_requires_evidence_for_existing_source_backed_items():
    source = "Decision: proceed. Action: Backend should patch. Risk: delay. Metric: 2.4%."
    summary = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        key_points=[KeyPoint(text="Decision: proceed.")],
        decisions=[Decision(text="Decision: proceed.")],
        actions=[ActionItem(action="Backend should patch.")],
        risks=[Risk(title="Risk: delay.")],
        metrics=[Metric(name="error_rate", value="2.4", unit="%")],
    )

    errors = validate_summary_evidence(summary, source)

    assert any("key point evidence is required" in error for error in errors)
    assert any("decision evidence is required" in error for error in errors)
    assert any("action evidence is required" in error for error in errors)
    assert any("risk evidence is required" in error for error in errors)
    assert any("metric evidence is required" in error for error in errors)


def test_validate_summary_allows_empty_claim_lists_without_evidence():
    summary = DocumentSummaryState(document_id="doc", content_fingerprint="abc", summary="Plain overview.")

    assert validate_summary_evidence(summary, "Plain overview.") == []
```

Add to `tests/test_pipeline_cache.py`:

```python
from document_briefing_cache.models import DocumentSummaryState, KeyPoint
from document_briefing_cache.summarizers import BaseSummarizer


class MissingEvidenceSummarizer(BaseSummarizer):
    summarizer_id = "missing-evidence-v1"

    def summarize(self, document, sections, content_fingerprint):
        return DocumentSummaryState(
            document_id=document.document_id or content_fingerprint[:16],
            content_fingerprint=content_fingerprint,
            summary="Unsupported item.",
            key_points=[KeyPoint(text="Unsupported item.")],
            summarizer_id=self.summarizer_id,
        )


def test_validation_errors_prevent_document_cache_write(tmp_path):
    docs = [DocumentInput(document_id="bad", title="Bad", text="Source text.")]
    pipeline = BriefingPipeline(cache_dir=tmp_path, summarizer=MissingEvidenceSummarizer())

    result = pipeline.run(docs, use_output_cache=False)

    assert result.stats.evidence_validation_errors > 0
    assert list((tmp_path / "document_summaries").glob("*.json")) == []
```

- [ ] **Step 2: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_evidence.py tests/test_pipeline_cache.py -q
```

Expected: FAIL because missing evidence is currently accepted.

- [ ] **Step 3: Implement strict evidence requirement**

In `src/document_briefing_cache/evidence.py`, add a helper:

```python
def _has_source_evidence(evidence_refs: list[EvidenceRef]) -> bool:
    return any(bool(ref.quote) for ref in evidence_refs)
```

At the start of `validate_summary_evidence`, after maps are built:

```python
for idx, point in enumerate(summary.key_points):
    if point.text and not _has_source_evidence(point.evidence):
        errors.append(f"key point evidence is required: {idx}")
for idx, decision in enumerate(summary.decisions):
    if decision.text and not _has_source_evidence(decision.evidence):
        errors.append(f"decision evidence is required: {idx}")
for idx, action in enumerate(summary.actions):
    if action.action and not _has_source_evidence(action.evidence):
        errors.append(f"action evidence is required: {idx}")
for idx, risk in enumerate(summary.risks):
    if risk.title and not _has_source_evidence(risk.evidence):
        errors.append(f"risk evidence is required: {idx}")
for idx, metric in enumerate(summary.metrics):
    if metric.value and not _has_source_evidence(metric.evidence):
        errors.append(f"metric evidence is required: {idx}")
```

Keep `summary` and `sections_digest` out of this task.

- [ ] **Step 4: Update OpenAI prompt**

In `OpenAIStructuredSummarizer.system_prompt`, add:

```text
Every key point, decision, action, risk, and metric must include at least one evidence quote from the supplied sections.
```

- [ ] **Step 5: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_evidence.py tests/test_pipeline_cache.py tests/test_openai_structured_summarizer.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/document_briefing_cache/evidence.py src/document_briefing_cache/summarizers.py tests/test_evidence.py tests/test_pipeline_cache.py
git commit -m "feat: require evidence for structured claims"
```

---

### Task 9: Introduce Schema v1.1 Summary And Section Evidence

**Files:**
- Modify: `src/document_briefing_cache/models.py`
- Modify: `src/document_briefing_cache/evidence.py`
- Modify: `src/document_briefing_cache/summarizers.py`
- Modify: `src/document_briefing_cache/pipeline.py`
- Modify: `src/document_briefing_cache/hashing.py`
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_pipeline_cache.py`
- Modify: `tests/test_openai_structured_summarizer.py`
- Modify: `references/schema.md`
- Modify: `references/llm-contract.md`
- Modify: `README.md`

- [ ] **Step 1: Add failing v1.1 tests**

Add to `tests/test_evidence.py`:

```python
def test_schema_v11_requires_summary_and_section_digest_evidence():
    source = "Decision: proceed."
    summary = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        schema_version="1.1.0",
        summary="Decision: proceed.",
        sections_digest=[SectionDigest(section_id="s1", summary="Decision: proceed.")],
    )

    errors = validate_summary_evidence(summary, source, sections=[DocumentSection(section_id="s1", order=0, text=source)])

    assert any("summary evidence is required" in error for error in errors)
    assert any("section digest evidence is required" in error for error in errors)


def test_schema_v11_validates_summary_evidence_quotes():
    source = "Decision: proceed."
    sections = [DocumentSection(section_id="s1", order=0, text=source)]
    summary = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        schema_version="1.1.0",
        summary="Decision: proceed.",
        summary_evidence=[EvidenceRef(document_id="doc", section_id="s1", quote="Decision: proceed.")],
        sections_digest=[
            SectionDigest(
                section_id="s1",
                summary="Decision: proceed.",
                evidence=[EvidenceRef(document_id="doc", section_id="s1", quote="Decision: proceed.")],
            )
        ],
    )

    assert validate_summary_evidence(summary, source, sections=sections) == []
```

Add to `tests/test_pipeline_cache.py`:

```python
def test_schema_100_cached_summary_is_treated_as_miss_after_v11(tmp_path):
    from document_briefing_cache.cache import JsonFileCache
    from document_briefing_cache.hashing import document_content_fingerprint, document_summary_cache_key
    from document_briefing_cache.pipeline import SKILL_VERSION

    docs = [DocumentInput(document_id="schema", title="Schema", text="Decision: proceed.")]
    fingerprint = document_content_fingerprint(docs[0])
    key = document_summary_cache_key(
        docs[0],
        fingerprint=fingerprint,
        summarizer_id="counting-rules-v1",
        skill_version=SKILL_VERSION,
    )
    old_summary = DocumentSummaryState(
        schema_version="1.0.0",
        document_id="schema",
        content_fingerprint=fingerprint,
        summary="Old schema.",
        summarizer_id="counting-rules-v1",
    )
    JsonFileCache(tmp_path, "document_summaries").set_model(key, old_summary)

    result = BriefingPipeline(cache_dir=tmp_path, summarizer=CountingSummarizer()).run(docs, use_output_cache=False)

    assert result.stats.document_cache_hits == 0
    assert result.stats.document_cache_misses == 1
    assert result.stats.document_cache_corrupt == 1
```

- [ ] **Step 2: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_evidence.py tests/test_pipeline_cache.py -q
```

Expected: FAIL until v1.1 fields and validation exist.

- [ ] **Step 3: Add schema version constant and fields**

In `src/document_briefing_cache/models.py`:

```python
DOCUMENT_SUMMARY_SCHEMA_VERSION = "1.1.0"
```

Modify:

```python
class SectionDigest(BaseModel):
    section_id: str
    heading: str | None = None
    summary: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
```

Modify:

```python
class DocumentSummaryState(BaseModel):
    schema_version: str = DOCUMENT_SUMMARY_SCHEMA_VERSION
    document_id: str
    content_fingerprint: str
    title: str | None = None
    source: str | None = None
    doc_type: DocumentType | str = DocumentType.unknown
    content_format: ContentFormat | str = ContentFormat.unknown
    language: str = "unknown"
    summary: str = ""
    summary_evidence: list[EvidenceRef] = Field(default_factory=list)
```

- [ ] **Step 4: Use the schema constant in hashing and pipeline**

In `src/document_briefing_cache/hashing.py`, import the constant and set the default:

```python
from .models import DOCUMENT_SUMMARY_SCHEMA_VERSION, DocumentInput, DocumentSummaryState


def document_summary_cache_key(
    document: DocumentInput,
    fingerprint: str,
    summarizer_id: str,
    skill_version: str,
    schema_version: str = DOCUMENT_SUMMARY_SCHEMA_VERSION,
    redaction_policy_id: str = "none",
) -> str:
```

In `src/document_briefing_cache/pipeline.py`, replace hardcoded `"1.0.0"` in `_cached_summary_matches` with `DOCUMENT_SUMMARY_SCHEMA_VERSION`.

- [ ] **Step 5: Produce v1.1 evidence in rule summarizer**

In `RuleBasedExtractiveSummarizer.summarize`, create summary evidence from the first selected summary sentence:

```python
summary_evidence = [
    evidence(doc_id, find_section_for_sentence(sections, sentence), document.source, sentence)
    for sentence in summary_sentences[:1]
]
```

Set `summary_evidence=summary_evidence`.

For `SectionDigest`, add evidence using the selected section sentence:

```python
section_sentence = " ".join(select_summary_sentences(split_sentences(section.text), limit=1)) or section.text[:160]
SectionDigest(
    section_id=section.section_id,
    heading=section.heading,
    summary=section_sentence,
    evidence=[evidence(doc_id, section, document.source, section_sentence)] if section_sentence else [],
)
```

- [ ] **Step 6: Validate v1.1 summary and section digest evidence**

In `src/document_briefing_cache/evidence.py`, include `summary.summary_evidence` and each `digest.evidence` in `_iter_evidence`.

In `validate_summary_evidence`:

```python
if summary.schema_version >= "1.1.0":
    if summary.summary and not _has_source_evidence(summary.summary_evidence):
        errors.append("summary evidence is required")
    for idx, digest in enumerate(summary.sections_digest):
        if digest.summary and not _has_source_evidence(digest.evidence):
            errors.append(f"section digest evidence is required: {idx}")
```

- [ ] **Step 7: Update OpenAI adapter tests and prompt**

Update `tests/test_openai_structured_summarizer.py` expected payload to include:

```python
"schema_version": "1.1.0",
"summary_evidence": [],
```

Each section digest object should include `"evidence": []` if present.

Update the prompt to require `summary_evidence` and `sections_digest[].evidence`.

- [ ] **Step 8: Update docs**

Document schema v1.1 in `references/schema.md`, `references/llm-contract.md`, and README production notes.

- [ ] **Step 9: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_evidence.py tests/test_pipeline_cache.py tests/test_openai_structured_summarizer.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/document_briefing_cache/models.py src/document_briefing_cache/evidence.py src/document_briefing_cache/summarizers.py src/document_briefing_cache/pipeline.py src/document_briefing_cache/hashing.py
git add tests/test_evidence.py tests/test_pipeline_cache.py tests/test_openai_structured_summarizer.py references/schema.md references/llm-contract.md README.md
git commit -m "feat: add schema v1.1 claim evidence"
```

---

### Task 10: Harden OpenAI Adapter With Budgeting, Retry, And Merge

**Files:**
- Create: `src/document_briefing_cache/llm.py`
- Modify: `src/document_briefing_cache/summarizers.py`
- Modify: `src/document_briefing_cache/cli.py`
- Create: `tests/test_llm_chunking.py`
- Modify: `tests/test_openai_structured_summarizer.py`
- Modify: `tests/test_cli_cache.py`
- Modify: `references/llm-contract.md`
- Modify: `README.md`

- [ ] **Step 1: Add failing LLM utility tests**

Create `tests/test_llm_chunking.py`:

```python
from document_briefing_cache.llm import LLMConfig, chunk_sections_by_budget, estimate_tokens, merge_document_states
from document_briefing_cache.models import DocumentSection, DocumentSummaryState, EvidenceRef, KeyPoint


def test_estimate_tokens_is_deterministic_char_based_floor():
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_chunk_sections_by_budget_preserves_order():
    sections = [
        DocumentSection(section_id="s1", order=0, text="a" * 80),
        DocumentSection(section_id="s2", order=1, text="b" * 80),
        DocumentSection(section_id="s3", order=2, text="c" * 80),
    ]

    chunks = chunk_sections_by_budget(sections, LLMConfig(max_input_tokens=25))

    assert [[section.section_id for section in chunk] for chunk in chunks] == [["s1"], ["s2"], ["s3"]]


def test_merge_document_states_deduplicates_evidence_backed_items():
    evidence = [EvidenceRef(document_id="doc", section_id="s1", quote="Decision: proceed.")]
    left = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        summary="Decision: proceed.",
        summary_evidence=evidence,
        key_points=[KeyPoint(text="Decision: proceed.", evidence=evidence)],
        summarizer_id="openai-test",
    )
    right = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        summary="Decision: proceed.",
        summary_evidence=evidence,
        key_points=[KeyPoint(text="Decision: proceed.", evidence=evidence)],
        summarizer_id="openai-test",
    )

    merged = merge_document_states([left, right])

    assert merged.document_id == "doc"
    assert len(merged.key_points) == 1
    assert merged.content_fingerprint == "abc"
```

- [ ] **Step 2: Add failing OpenAI adapter tests**

Extend `tests/test_openai_structured_summarizer.py` with fake client tests for:

```python
def test_openai_summarizer_passes_timeout_and_max_output_tokens():
    client = RecordingClient(output_text=valid_state_json(document_id="doc", fingerprint="fingerprint"))
    summarizer = OpenAIStructuredSummarizer(
        model="test-model",
        client=client,
        llm_config=LLMConfig(timeout_seconds=12.5, max_output_tokens=321),
    )

    summarizer.summarize(DocumentInput(document_id="doc", text="Decision: proceed."), [], "fingerprint")

    request = client.responses.calls[0]
    assert request["max_output_tokens"] == 321
    assert request["timeout"] == 12.5


def test_openai_summarizer_retries_transient_provider_errors():
    client = FlakyClient(
        errors=[TransientProviderError(status_code=429)],
        output_text=valid_state_json(document_id="doc", fingerprint="fingerprint"),
    )
    summarizer = OpenAIStructuredSummarizer(model="test-model", client=client, llm_config=LLMConfig(max_retries=1))

    summarizer.summarize(DocumentInput(document_id="doc", text="Decision: proceed."), [], "fingerprint")

    assert len(client.responses.calls) == 2


def test_openai_summarizer_chunks_large_documents_before_provider_call():
    client = RecordingClient(output_text=valid_state_json(document_id="doc", fingerprint="fingerprint"))
    summarizer = OpenAIStructuredSummarizer(
        model="test-model",
        client=client,
        llm_config=LLMConfig(max_input_tokens=10),
    )
    sections = [
        DocumentSection(section_id="s1", order=0, text="a" * 80),
        DocumentSection(section_id="s2", order=1, text="b" * 80),
    ]

    summarizer.summarize(DocumentInput(document_id="doc", text="Decision: proceed."), sections, "fingerprint")

    assert len(client.responses.calls) == 2
```

Use a fake `responses.create` object that records calls and raises a custom exception with `status_code = 429` on the first call for retry testing.

- [ ] **Step 3: Run RED**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_llm_chunking.py tests/test_openai_structured_summarizer.py -q
```

Expected: FAIL because `llm.py` and adapter options do not exist.

- [ ] **Step 4: Implement LLM utility module**

Create `src/document_briefing_cache/llm.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from .models import DocumentSection, DocumentSummaryState


@dataclass(frozen=True)
class LLMConfig:
    timeout_seconds: float = 60.0
    max_retries: int = 2
    max_input_tokens: int = 12000
    max_output_tokens: int = 4000


def estimate_tokens(text: str) -> int:
    return max(1, (len(text or "") + 3) // 4)


def chunk_sections_by_budget(sections: list[DocumentSection], config: LLMConfig) -> list[list[DocumentSection]]:
    chunks: list[list[DocumentSection]] = []
    current: list[DocumentSection] = []
    current_tokens = 0
    for section in sections:
        section_tokens = estimate_tokens(section.text)
        if current and current_tokens + section_tokens > config.max_input_tokens:
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append(section)
        current_tokens += section_tokens
    if current:
        chunks.append(current)
    return chunks


def merge_document_states(partials: list[DocumentSummaryState]) -> DocumentSummaryState:
    if not partials:
        raise ValueError("Cannot merge empty DocumentSummaryState list.")
    first = partials[0].model_copy(deep=True)
    for partial in partials[1:]:
        if partial.document_id != first.document_id:
            raise ValueError("Cannot merge states with different document_id values.")
        if partial.content_fingerprint != first.content_fingerprint:
            raise ValueError("Cannot merge states with different content_fingerprint values.")
        first.summary = " ".join(part for part in [first.summary, partial.summary] if part).strip()
        first.summary_evidence.extend(partial.summary_evidence)
        first.key_points.extend(partial.key_points)
        first.decisions.extend(partial.decisions)
        first.actions.extend(partial.actions)
        first.risks.extend(partial.risks)
        first.metrics.extend(partial.metrics)
        first.entities = sorted(set(first.entities) | set(partial.entities))
        first.topics = sorted(set(first.topics) | set(partial.topics))
        first.open_questions.extend(question for question in partial.open_questions if question not in first.open_questions)
        first.unknowns.extend(unknown for unknown in partial.unknowns if unknown not in first.unknowns)
        first.sections_digest.extend(partial.sections_digest)
        first.importance = max(first.importance, partial.importance)
    first.key_points = _dedupe_by_text_and_quote(first.key_points)
    return first


def _dedupe_by_text_and_quote(items):
    seen: set[tuple[str, tuple[str, ...]]] = set()
    deduped = []
    for item in items:
        text = getattr(item, "text", None) or getattr(item, "action", None) or getattr(item, "title", None) or ""
        quotes = tuple(ref.quote or "" for ref in getattr(item, "evidence", []))
        key = (text, quotes)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
```

- [ ] **Step 5: Wire config into OpenAI summarizer**

Modify `OpenAIStructuredSummarizer.__init__`:

```python
def __init__(
    self,
    model: str | None = None,
    client=None,
    prompt_version: str = "prompt-v3",
    llm_config: LLMConfig | None = None,
):
    self.llm_config = llm_config or LLMConfig()
```

Split sections:

```python
batches = chunk_sections_by_budget(sections, self.llm_config)
states = [self._summarize_batch(document, batch, content_fingerprint, doc_id) for batch in batches]
state = states[0] if len(states) == 1 else merge_document_states(states)
```

Pass request options:

```python
response = self.client.responses.create(
    model=self.model,
    input=[
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, sort_keys=True)},
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "DocumentSummaryState",
            "schema": DocumentSummaryState.model_json_schema(),
            "strict": True,
        }
    },
    max_output_tokens=self.llm_config.max_output_tokens,
    truncation="disabled",
    store=False,
    timeout=self.llm_config.timeout_seconds,
)
```

Use request-level `timeout` in this implementation so the fake-client test can assert `request["timeout"] == llm_config.timeout_seconds`. If a future SDK version rejects request-level timeout, make that compatibility change in a separate follow-up with a new test.

- [ ] **Step 6: Implement bounded transient retries**

Add:

```python
def _is_transient_provider_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    return status in {408, 409, 429, 500, 502, 503, 504}
```

Wrap provider call with attempts `max_retries + 1`. Do not retry `json.JSONDecodeError`, Pydantic validation errors, document id mismatch, or content fingerprint mismatch.

- [ ] **Step 7: Add CLI flags**

In `src/document_briefing_cache/cli.py`:

```python
parser.add_argument("--openai-model", default=None)
parser.add_argument("--llm-timeout", type=float, default=60.0)
parser.add_argument("--llm-max-retries", type=int, default=2)
parser.add_argument("--llm-max-input-tokens", type=int, default=12000)
parser.add_argument("--llm-max-output-tokens", type=int, default=4000)
```

When `args.summary_mode == "openai"`:

```python
summarizer = OpenAIStructuredSummarizer(
    model=args.openai_model,
    llm_config=LLMConfig(
        timeout_seconds=args.llm_timeout,
        max_retries=args.llm_max_retries,
        max_input_tokens=args.llm_max_input_tokens,
        max_output_tokens=args.llm_max_output_tokens,
    ),
)
```

- [ ] **Step 8: Update docs**

In `references/llm-contract.md`, document chunk-map-merge, retry policy, timeout, and token budget.

In `README.md`, add an OpenAI production flags example.

- [ ] **Step 9: Run GREEN**

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_llm_chunking.py tests/test_openai_structured_summarizer.py tests/test_cli_cache.py -q
```

Expected: PASS.

- [ ] **Step 10: Optional live smoke**

Only run when explicitly available:

```bash
OPENAI_API_KEY="$OPENAI_API_KEY" python3 -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --summary-mode openai \
  --cache-policy ephemeral \
  --no-output-cache \
  --show-stats
```

Expected: command exits 0, `summarizer_calls` equals the number of cache misses, and no persistent output cache remains.

- [ ] **Step 11: Commit**

```bash
git add src/document_briefing_cache/llm.py src/document_briefing_cache/summarizers.py src/document_briefing_cache/cli.py
git add tests/test_llm_chunking.py tests/test_openai_structured_summarizer.py tests/test_cli_cache.py references/llm-contract.md README.md
git commit -m "feat: harden OpenAI summarizer path"
```

---

### Task 11: Final Verification And Release Readiness

**Files:**
- Modify: `VALIDATION.md`

- [ ] **Step 1: Run full local verification**

Run:

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/validate_skill.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/validate_skill.py --run-evals
python3 -m build
```

Expected:

```text
73 passed
OK: briefprint skill repository validated (updated test/eval counts)
OK: briefprint skill repository validated (updated test/eval counts)
```

The test count will be higher than 73 after this plan lands; update `VALIDATION.md` with the observed value.

- [ ] **Step 2: Run installed wheel smoke from outside the repo**

Run:

```bash
python3 -m venv /tmp/dbc-final-wheel
/tmp/dbc-final-wheel/bin/python -m pip install dist/*.whl
cd /tmp
/tmp/dbc-final-wheel/bin/python - <<'PY'
from document_briefing_cache.models import DocumentInput
from document_briefing_cache.pipeline import BriefingPipeline
result = BriefingPipeline(cache_dir="/tmp/dbc-final-cache").run(
    [DocumentInput(document_id="final", title="Final", text="Action: final smoke.")],
    mode="brief",
    use_output_cache=False,
)
assert "문서 브리핑" in result.output
PY
```

Expected: exits 0.

- [ ] **Step 3: Update validation record**

Update `VALIDATION.md` with:

- current date,
- Python version,
- full pytest result,
- `validate_skill.py` result,
- `validate_skill.py --run-evals` result,
- wheel/sdist smoke result,
- note that live OpenAI smoke is optional and only recorded when credentials are available.

- [ ] **Step 4: Inspect final diff**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Expected: no whitespace errors from `git diff --check`.

- [ ] **Step 5: Commit validation update**

```bash
git add VALIDATION.md
git commit -m "docs: record hardening validation"
```

---

## Final Acceptance Criteria

- Installed wheel and sdist render templates without relying on root `templates/`.
- CI runs source tests, validation evals, and installed distribution smoke.
- CLI rejects `http://` and `https://` values passed to `--input` with a clear non-fetching message.
- README/SKILL describe URL-bearing metadata honestly and do not imply remote fetch support.
- Fallback normalization records `metadata.normalization_unknowns`, and the pipeline preserves those values in `DocumentSummaryState.unknowns`.
- Privacy docs clearly state the `basic-contact-v1` scope and the limits of HMAC.
- Existing structured claim fields require source evidence before cache write.
- Schema v1.1 adds source evidence for `summary` and `sections_digest`.
- Stale schema v1.0 cache entries are rejected as misses.
- OpenAI adapter has fake-client coverage for chunking, timeout/max-output request options, transient retry, and merge validation.
- Repeated document requests and template-only rerenders still produce `summarizer_calls = 0`.
