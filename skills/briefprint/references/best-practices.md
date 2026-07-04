# Best Practices

## Prefer Exact Cache for Data-Sensitive Content

For dates, metrics, incidents, policies, finance, legal, and current operational data, use exact fingerprints. Semantic cache can be unsafe when small differences matter.

## Treat Prompt Caching as Secondary

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
- cache-miss input-token estimates,
- naive re-summarization input-token estimates,
- protected-value and evidence validation failures,
- quality warnings for shallow extraction.

Token estimates from a local harness are not provider billing telemetry. Use provider usage or host telemetry when exact billing matters.

## Treat Cache as Sensitive

Document summaries can contain evidence quotes, names, IDs, dates, metrics, sources, and rendered outputs. Prefer private cache permissions, short output-cache TTLs, and ephemeral mode for sensitive documents.

Use redaction before cache-miss summarization when documents may contain PII or secrets. Use encrypted storage or tmpfs when cache contents need confidentiality. HMAC detects tampering only; it does not hide contents.
