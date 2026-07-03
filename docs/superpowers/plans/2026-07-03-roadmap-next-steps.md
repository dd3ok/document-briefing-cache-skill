# Roadmap Next Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement the next lightweight exact-cache roadmap items: demo, cache explain, workflow evals, incident record splitting, metadata tightening, and a thin sensitive alias.

**Architecture:** Keep the existing exact-cache pipeline intact. Add observable stats/events, deterministic examples, and narrow normalization helpers without introducing services, databases, broad DSLs, semantic cache, RAG, or provider telemetry.

**Tech Stack:** Python 3.10+, Pydantic, pytest, existing CLI and JSON file cache.

## Global Constraints

- Work on branch `codex/roadmap-next-steps`.
- Use TDD for behavior changes: write failing tests first, verify failure, then implement.
- Keep `SKILL.md` compact; longer guidance belongs in `README.md`, `examples/`, or `references/`.
- Do not add dependencies.
- Do not implement facts schema, coverage profile DSL, provider telemetry, redact-secrets, semantic cache, RAG, URL fetching, dashboard, or service.
- Every new behavior must have deterministic local tests.

---

### Task 1: Incident Lifecycle Demo

**Files:**
- Create: `examples/incident_lifecycle/initial.json`
- Create: `examples/incident_lifecycle/update.json`
- Create: `examples/incident_lifecycle/with_update.json`
- Create: `examples/incident_lifecycle/README.md`
- Modify: `README.md`
- Test: `tests/test_examples.py`

**Interfaces:**
- Consumes: existing `document_briefing_cache.cli.main`, `benchmark` command.
- Produces: a demo that shows cold run, rerender, and add-one-update cache behavior.

- [x] **Step 1: Write failing test**

Add `tests/test_examples.py` with a test that runs the benchmark against the demo files and asserts:

```python
payload["rows"][0]["summarizer_calls"] == 2
payload["rows"][1]["summarizer_calls"] == 0
payload["rows"][-2]["summarizer_calls"] == 1
payload["rows"][-2]["document_cache_hits"] == 2
payload["rows"][-2]["document_cache_misses"] == 1
```

- [x] **Step 2: Verify failure**

Run: `python -m pytest tests\test_examples.py -q`
Expected: fail because demo files do not exist.

- [x] **Step 3: Add demo files and README link**

Create the three JSON fixtures and an example README with the exact benchmark command. Link the demo from the root README benchmark section.

- [x] **Step 4: Verify pass**

Run: `python -m pytest tests\test_examples.py -q`
Expected: pass.

---

### Task 2: Cache Explain Events And CLI Output

**Files:**
- Modify: `src/document_briefing_cache/models.py`
- Modify: `src/document_briefing_cache/pipeline.py`
- Modify: `src/document_briefing_cache/cli.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_cli.py` or existing CLI test file

**Interfaces:**
- Consumes: `PipelineStats`, `BriefingPipeline.run`, CLI `run`.
- Produces: `document_cache_events`, `output_cache_event`, and `--explain-cache` text output.

- [x] **Step 1: Write failing model/pipeline tests**

Tests must assert document events for `miss`, `hit`, `refresh`, `bypass`, and `ephemeral` policies using enum-like reason strings:

```text
miss_new_fingerprint
hit_same_contract
miss_refresh_policy
miss_bypass_policy
miss_ephemeral_policy
```

- [x] **Step 2: Write failing CLI test**

Run CLI with `--show-stats --explain-cache` and assert the output contains `Cache explanation`, document id, status, fingerprint prefix, and reason.

- [x] **Step 3: Verify failure**

Run targeted tests and confirm missing fields/argument failures.

- [x] **Step 4: Implement minimal stats events**

Add Pydantic event models or dict fields to `PipelineStats`, populate them in the pipeline, and print a small Markdown table in CLI.

- [x] **Step 5: Verify pass**

Run targeted pipeline/CLI tests.

---

### Task 3: Workflow And Nuance Evals

**Files:**
- Modify: `evals/briefing_eval_cases.json`
- Modify: `scripts/validate_skill.py` if needed for new eval expectations
- Test: `tests/test_evals.py` or existing validation tests

**Interfaces:**
- Consumes: existing eval format and validation script.
- Produces: deterministic fixtures for mitigated/resolved, not-observed/false, and add-one-update cache trust.

- [x] **Step 1: Write failing validation test**

Add fixture expectations that fail if:

```text
Mitigated becomes Resolved.
No duplicate charges observed becomes no duplicate charges.
Legal communication restriction is dropped.
```

- [x] **Step 2: Verify failure**

Run: `python scripts\validate_skill.py`
Expected: fail until eval fixtures and/or validation logic are added.

- [x] **Step 3: Add minimal eval cases**

Use existing eval schema where possible. If validation script needs a small string absence assertion, add it narrowly.

- [x] **Step 4: Verify pass**

Run: `python scripts\validate_skill.py` and targeted tests.

---

### Task 4: Incident-Only Record Split

**Files:**
- Modify: `src/document_briefing_cache/normalize.py`
- Modify: `src/document_briefing_cache/cli.py`
- Test: `tests/test_normalize.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `DocumentInput`, existing section split.
- Produces: `--split-records incident` for stable incident update boundaries only.

- [x] **Step 1: Write failing normalization tests**

Tests must assert:

```text
Incident ID: INC-1
Incident Update: 2026-07-03 15:30
```

splits into stable ids like:

```text
INC-1/root
INC-1/update-2026-07-03-15-30
```

- [x] **Step 2: Write failing benchmark CLI test**

Benchmark append-only incident updates with `--split-records incident` and assert previous records hit while the new record misses.

- [x] **Step 3: Verify failure**

Run targeted tests and confirm CLI rejects or lacks the option.

- [x] **Step 4: Implement narrow splitter**

Add `split_documents_into_incident_records` and CLI choices `none` and `incident`. Do not add `auto`, ticket, or Markdown modes.

- [x] **Step 5: Verify pass**

Run targeted normalize/benchmark tests.

---

### Task 5: Metadata Tightening And Sensitive Alias

**Files:**
- Modify: `agents/openai.yaml`
- Modify: `src/document_briefing_cache/cli.py`
- Modify: `README.md`
- Test: `tests/test_skill_metadata.py`
- Test: CLI tests

**Interfaces:**
- Consumes: existing cache-policy, output-cache, redact-pii, delete-on-exit options.
- Produces: clearer skill metadata and `--sensitive` alias.

- [x] **Step 1: Write failing tests**

Tests must assert:

```text
agents/openai.yaml short_description mentions rerender/re-summarizing unchanged documents.
--sensitive expands to ephemeral cache policy, no output cache, redact_pii, delete_on_exit created.
```

- [x] **Step 2: Verify failure**

Run targeted metadata/CLI tests.

- [x] **Step 3: Implement minimal alias and metadata text**

Do not add secret redaction or privacy claims. Print sensitive mode only through existing stats fields.

- [x] **Step 4: Verify pass**

Run targeted tests.

---

### Task 6: Final Review And Verification

**Files:**
- No planned production files.

**Interfaces:**
- Consumes: full branch diff.
- Produces: final verification evidence and subagent review results.

- [x] **Step 1: Run validation**

Run:

```powershell
python scripts\validate_skill.py
python -m pytest -q
python -m ruff check .
```

- [x] **Step 2: Dispatch subagent reviews**

Ask at least two subagents:

```text
code-reviewer: correctness/regression review of full diff.
test-engineer: test adequacy and roadmap acceptance review.
```

- [x] **Step 3: Fix blocking findings**

Fix Critical/Important findings and rerun relevant checks.

- [x] **Step 4: Self-review**

Check the branch against the roadmap non-goals and global constraints.
