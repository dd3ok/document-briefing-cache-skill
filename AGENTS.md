# Agent Instructions

Use this repository as a compact skill for repeated document briefing tasks.

## Agent behavior

When a user asks to summarize, brief, digest, recap, or rerender documents:

1. Normalize the input into `DocumentInput`.
2. Compute a stable document fingerprint.
3. Check `DocumentSummaryState` cache.
4. Summarize only cache misses.
5. Render from templates.
6. Report cache stats when useful.

## Important constraints

- Do not call an LLM for a repeated document.
- Do not call an LLM for template-only changes.
- Do not collapse all documents into one giant prompt if document-level caching is possible.
- Store structured state, not just final strings.
- Preserve IDs, names, dates, and numeric values.

## Safe default

If an input type is unfamiliar, still normalize it to text plus metadata and mark uncertainties in `unknowns`.
