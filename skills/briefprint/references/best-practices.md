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

The skill bundle is static install-time guidance. Briefprint's runtime cache lives under `--cache-dir`; it is created by the CLI/runtime, not by the installed skill bundle. Installing, updating, or removing the agent skill does not migrate, prune, or delete runtime caches. No portable agent-skill host contract currently provides automatic eviction for generated document state. Do not write document caches into the installed skill directory.

Prefer clear invocation examples and boundaries over broad auto-routing cues. For manual-only hosts, the description is for discoverability and manual invocation guidance, not for broad automatic routing.

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

Secret redaction can mask operational correlation IDs such as `session_id`; enable it only when secret protection outweighs exact correlation.
