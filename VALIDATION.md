# Validation

Last verified: 2026-05-11

Environment:

- Python 3.14.4
- Installed with `python3 -m pip install --user --break-system-packages -e ".[dev]"`
- Pytest capture used `TMPDIR=/tmp` so temp files are created on a POSIX filesystem.

Commands:

```bash
TMPDIR=/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/validate_skill.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/validate_skill.py --run-evals
```

Observed result:

```text
35 passed in 0.27s
OK: document briefing cache skill repository validated (9 test files, 4 eval cases)
OK: document briefing cache skill repository validated (9 test files, 4 eval cases)
```

Smoke test using `examples/mixed_documents.json` and a fresh cache:

```text
1st run, mode=brief:
  output_cache_hit: false
  document_cache_hits: 0
  document_cache_misses: 3
  document_cache_corrupt: 0
  summarizer_calls: 3

2nd run, same mode=brief:
  output_cache_hit: true
  summarizer_calls: 0

3rd run, changed mode=action_items:
  output_cache_hit: false
  document_cache_hits: 3
  document_cache_misses: 0
  document_cache_corrupt: 0
  summarizer_calls: 0
```

Expected properties:

- The skill metadata exists in `SKILL.md`.
- Trigger boundaries avoid source-code review, live lookup, and non-document Q&A.
- The implementation has deterministic document fingerprints.
- Repeated documents are served from document-level cache.
- Re-rendering from another template does not trigger re-summarization.
- Cached summaries are rejected when fingerprint, schema, document id, or summarizer id does not match.
- Cache envelopes include payload digests and private POSIX permissions where the filesystem supports them.
- Rendered Markdown escapes untrusted document/model fields.
- The default rules summarizer can run without an LLM or network access.
- The repository includes templates, references, tests, examples, evals, and a CLI.

Production validation should continue adding real samples from the target domain and compare:

- factual preservation,
- missing-value behavior,
- action item extraction,
- risk extraction,
- LLM call count,
- cache hit rate,
- output readability,
- privacy and retention expectations.
