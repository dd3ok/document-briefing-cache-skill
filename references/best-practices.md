# Best Practices

## 1. Cache at the document level

Do not cache only final outputs. Final-output cache is useful, but document-level cache is what prevents re-summarizing unchanged documents.

## 2. Separate meaning from rendering

Summarization creates structured meaning. Rendering creates presentation.

```text
DocumentSummaryState → brief / digest / executive / action_items / debug
```

## 3. Keep LLM output structured

A final paragraph is hard to reuse. A structured state can be filtered, sorted, and rendered without further LLM calls.

## 4. Use exact cache for data-sensitive content

For dates, metrics, incidents, policies, finance, legal, and current data, prefer exact fingerprints. Semantic cache can be unsafe when small differences matter.

## 5. Use semantic cache only for safe repeated explanations

Semantic cache is better for FAQ-style answers than for fresh document summaries.

## 6. Use provider prompt caching only as a secondary optimization

Provider prompt caching can reduce repeated prefix cost, but it is not the same as zero-token reuse. Exact local cache remains the primary mechanism.

## 7. Keep skills small

A good skill should be easy to inspect:

- short `SKILL.md`,
- clear trigger phrases,
- minimal scripts,
- concrete schemas,
- tests that prove behavior.

## 8. Validate with real samples

Create a small evaluation set from actual documents and track:

- hallucinated facts,
- number/date preservation,
- action extraction accuracy,
- risk extraction accuracy,
- structured-state assertions for actions, risks, metrics, evidence, and unknowns,
- cache hit rate,
- LLM call count,
- output usability.

Static trigger evals should cover intended trigger and near-miss boundary cases. Treat them as metadata fixtures, not as proof of actual model-side skill invocation behavior.

Keep a separate manual benchmark worksheet for actual model-side invocation behavior. Record host, model, date, observed invocation, and notes because routing behavior is provider- and version-specific.

## 9. Treat cache as sensitive

Document summaries can contain evidence quotes, names, IDs, dates, metrics, sources, and rendered outputs. Prefer private cache permissions, short output-cache TTLs, and `ephemeral` mode for sensitive documents.

Use `--redact-pii` when basic contact information should not reach LLM cache-miss calls or local cache files. Redaction is a profile, so include its policy id in document and output cache keys.

Use HMAC-signed cache envelopes when local tamper detection matters. Sign the payload and security-relevant metadata such as namespace, key, cache version, payload digest, and expiry. HMAC is not encryption; cache files remain plaintext unless the deployment provides encrypted storage, tmpfs, or another encrypted backend.

## 10. Render untrusted fields safely

Document titles, sources, summaries, actions, and risk text may contain raw HTML or Markdown injection. Escape model- and user-derived fields before rendering Markdown for downstream tools.

## 11. Prepare short deployment descriptions

Codex/OpenAI skill metadata can use a detailed `SKILL.md` description for precise triggering. Claude.ai upload flows may require a shorter description, so keep a 200-character-safe variant ready for packaging.
