# Cache Lifecycle And Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a practical cache lifecycle layer and evidence validation gate so cached document summaries can be retained, expired, or deleted safely.

**Architecture:** Keep the compact JSON cache as the default backend, but add metadata envelopes, TTL/prune/clear behavior, and an explicit `CacheConfig`. Add deterministic protected-value and evidence validation before successful summaries are cached. SQLite remains a future managed backend rather than this implementation's default.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, Jinja2, BeautifulSoup.

---

### Task 1: Evidence Validation

**Files:**
- Create: `src/document_briefing_cache/evidence.py`
- Modify: `src/document_briefing_cache/__init__.py`
- Test: `tests/test_evidence.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert protected values are extracted from text and JSON-like raw payloads, evidence quotes must exist in the referenced section text, and hallucinated metric/date/ID values are reported as validation errors.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_evidence.py -q`

Expected: FAIL because `document_briefing_cache.evidence` does not exist.

- [ ] **Step 3: Implement minimal evidence module**

Implement `ProtectedValue`, `extract_protected_values`, `validate_summary_evidence`, and helpers for dates, IDs, percentages, currency, durations, and plain numbers.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m pytest tests/test_evidence.py -q`

Expected: PASS.

### Task 2: Cache Lifecycle

**Files:**
- Modify: `src/document_briefing_cache/models.py`
- Modify: `src/document_briefing_cache/cache.py`
- Modify: `src/document_briefing_cache/pipeline.py`
- Test: `tests/test_cache_lifecycle.py`

- [ ] **Step 1: Write failing tests**

Add tests for TTL expiry, ephemeral cleanup of created entries, clearing/pruning by namespace, and output cache disabled by default for new lifecycle config.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_cache_lifecycle.py -q`

Expected: FAIL because `CacheConfig` and lifecycle methods do not exist.

- [ ] **Step 3: Implement minimal lifecycle support**

Add `CacheConfig`, `CacheEntryInfo`, `PruneResult`, JSON envelope reads/writes with legacy bare JSON compatibility, `delete`, `clear`, `stats`, and `prune`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m pytest tests/test_cache_lifecycle.py -q`

Expected: PASS.

### Task 3: Pipeline And CLI Integration

**Files:**
- Modify: `src/document_briefing_cache/pipeline.py`
- Modify: `src/document_briefing_cache/cli.py`
- Modify: `README.md`
- Test: `tests/test_pipeline_cache.py`
- Test: `tests/test_cli_cache.py`

- [ ] **Step 1: Write failing tests**

Add pipeline tests proving expired cache misses are reported, ephemeral runs delete created entries, and CLI cache subcommands expose `stats`, `prune`, and `clear`.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_pipeline_cache.py tests/test_cli_cache.py -q`

Expected: FAIL because CLI flags/subcommands are missing.

- [ ] **Step 3: Implement pipeline/CLI changes**

Wire `CacheConfig` into `BriefingPipeline`, default rendered output cache off, add `--cache-policy`, `--document-ttl`, `--output-ttl`, `--prune-on-start`, `--delete-on-exit`, and `cache stats/prune/clear` subcommands.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m pytest tests/test_pipeline_cache.py tests/test_cli_cache.py -q`

Expected: PASS.

### Task 4: Full Verification

**Files:**
- All modified files

- [ ] **Step 1: Run validation script**

Run: `python scripts/validate_skill.py`

Expected: `OK: document briefing cache skill repository validated`

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Run sample command twice**

Run sample with `--show-stats` and verify the second run has no summarizer calls for unexpired document summaries.
