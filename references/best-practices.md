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
- cache hit rate,
- LLM call count,
- output usability.
