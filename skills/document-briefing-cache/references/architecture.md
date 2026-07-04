# Architecture

The skill is intentionally small:

```text
normalize -> fingerprint -> cache -> summarize cache misses -> render
```

## Normalize

All inputs become `DocumentInput` with text plus metadata. Preserve titles, sources, document type, content format, raw payload references, and normalization unknowns.

## Fingerprint

Compute a stable `content_fingerprint` from normalized content and identity-bearing metadata before summary work. The fingerprint is the cache boundary for repeated documents.

## Cache

Use document-level summary cache as the primary layer. A rendered-output cache is optional and secondary because rendering is cheap, while summary generation is expensive.

```text
document fingerprint + schema version + summarizer id -> DocumentSummaryState
document set + render mode + template version -> rendered output
```

## Summarize

The summarizer must emit structured `DocumentSummaryState`. A deterministic rules summarizer is acceptable for demos and validation. An LLM summarizer belongs only at cache misses.

## Render

Render templates from structured state. Changing the audience, format, or mode should not require re-summarizing unchanged documents.
