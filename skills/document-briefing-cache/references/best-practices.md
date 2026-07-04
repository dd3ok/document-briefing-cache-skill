# Best Practices

## Cache at the Document Level

Do not cache only final outputs. Final-output cache is useful, but document-level cache is what prevents re-summarizing unchanged documents.

## Separate Meaning From Rendering

```text
DocumentSummaryState -> brief / digest / executive / action_items / debug
```

Summarization creates reusable meaning. Rendering creates presentation.

## Keep Output Structured

A final paragraph is hard to reuse. Structured state can be filtered, sorted, grouped, and rerendered without another LLM call.

## Prefer Exact Cache for Data-Sensitive Content

For dates, metrics, incidents, policies, finance, legal, and current operational data, use exact fingerprints. Semantic cache can be unsafe when small differences matter.

## Treat Provider Prompt Caching as Secondary

Provider prompt caching can reduce repeated prefix cost, but it is not zero-token local reuse. Exact document-summary cache remains the primary mechanism.

## Keep the Skill Small

Install only the skill surface:

- concise `SKILL.md`,
- small references,
- optional metadata,
- no tests, validation harness, benchmark fixtures, or runtime source unless the host explicitly needs them.

## Interpret Benchmarks Carefully

Track at least:

- document cache hits and misses,
- summarizer calls,
- estimated cache-miss input tokens,
- naive re-summarization input tokens,
- protected-value and evidence validation failures,
- quality warnings for shallow extraction.

Token estimates from a local harness are not provider billing telemetry. Use provider usage or host telemetry when exact billing matters.

## Treat Cache as Sensitive

Document summaries can contain evidence quotes, names, IDs, dates, metrics, sources, and rendered outputs. Prefer private cache permissions, short output-cache TTLs, and ephemeral mode for sensitive documents.

Use redaction profiles before cache-miss summarization when documents may contain PII or secrets. Use encrypted storage or tmpfs when cache contents need confidentiality. HMAC detects tampering only; it does not hide contents.
