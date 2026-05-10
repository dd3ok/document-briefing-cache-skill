# Validation

This repository was validated with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
import os, pytest
ret = pytest.main(['-q'])
print(f'PYTEST_EXIT_CODE={ret}', flush=True)
os._exit(ret)
PY

PYTHONPATH=src python scripts/validate_skill.py
```

Observed result:

```text
13 passed in 0.62s
PYTEST_EXIT_CODE=0
OK: document briefing cache skill repository validated
```

Smoke test using `examples/mixed_documents.json`:

```text
1st run, mode=brief:
  output_cache_hit: false
  document_cache_hits: 0
  document_cache_misses: 3
  summarizer_calls: 3

2nd run, same mode=brief:
  output_cache_hit: true
  summarizer_calls: 0

3rd run, changed mode=action_items:
  output_cache_hit: false
  document_cache_hits: 3
  document_cache_misses: 0
  summarizer_calls: 0
```

Expected properties:

- The skill metadata exists in `SKILL.md`.
- The implementation has deterministic document fingerprints.
- Repeated documents are served from document-level cache.
- Re-rendering from another template does not trigger re-summarization.
- The default rules summarizer can run without an LLM or network access.
- The repository includes templates, references, tests, examples, and a CLI.

Production validation should add real samples from the target domain and compare:

- factual preservation,
- missing-value behavior,
- action item extraction,
- risk extraction,
- LLM call count,
- cache hit rate,
- output readability.
