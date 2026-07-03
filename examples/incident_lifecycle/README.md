# Incident Lifecycle Demo

This demo shows the core exact-cache workflow:

1. First run summarizes the ticket and incident report.
2. Same document set plus another render mode reuses cached structured state.
3. Adding one update summarizes only the new document.

Run:

```bash
python -m document_briefing_cache.cli benchmark \
  --input examples/incident_lifecycle/initial.json \
  --incremental-input examples/incident_lifecycle/update.json \
  --cache-dir .cache/incident-lifecycle-demo \
  --fresh \
  --mode brief \
  --mode action_items \
  --json
```

Expected cache shape:

```text
cold brief base:
  summarizer_calls: 2
  document_cache_hits: 0
  document_cache_misses: 2

same brief base:
  summarizer_calls: 0
  output_cache_hit: true

rerender action_items base:
  summarizer_calls: 0
  document_cache_hits: 2

add incremental brief:
  summarizer_calls: 1
  document_cache_hits: 2
  document_cache_misses: 1

rerender debug combined:
  summarizer_calls: 0
  document_cache_hits: 3
```

Use `with_update.json` when you want the combined input as a single file.
