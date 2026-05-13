# Schema

## DocumentInput

```json
{
  "document_id": "optional stable id",
  "title": "optional title",
  "source": "optional URL/path/source",
  "doc_type": "report | meeting_notes | email | ticket | log | policy | api_payload | news | web_page | transcript | review_comments | unknown",
  "content_format": "text | markdown | html | json | xml | pdf_text | unknown",
  "text": "normalized text",
  "raw": "optional original payload",
  "metadata": {}
}
```

## DocumentSummaryState

Current schema version: `1.1.0`.

```json
{
  "schema_version": "1.1.0",
  "document_id": "stable id",
  "content_fingerprint": "sha256",
  "title": "title",
  "source": "source",
  "doc_type": "document type",
  "content_format": "input format",
  "language": "ko | en | unknown",
  "summary": "brief summary",
  "summary_evidence": [{"document_id": "", "section_id": "", "source": null, "path": null, "quote": ""}],
  "key_points": [{"text": "", "evidence": []}],
  "decisions": [{"text": "", "owner": null, "evidence": []}],
  "actions": [{"action": "", "owner": null, "due": null, "status": "open", "evidence": []}],
  "risks": [{"title": "", "reason": null, "severity": "unknown", "evidence": []}],
  "metrics": [{"name": null, "value": "", "unit": null, "evidence": []}],
  "entities": [],
  "topics": [],
  "open_questions": [],
  "unknowns": [],
  "sections_digest": [{"section_id": "", "heading": null, "summary": "", "evidence": []}],
  "importance": 3,
  "summarizer_id": "rules-extractive-v0.2.0"
}
```

In schema `1.1.0`, a non-empty top-level `summary` requires `summary_evidence`, and each non-empty `sections_digest[].summary` requires `sections_digest[].evidence`. Evidence quotes must be copied verbatim from the matching source section.

## Design rule

Do not store only the final natural-language paragraph. Store this state, then render paragraphs from it.

`review_comments` means exported review feedback, PR discussion, or comment-thread documents. It does not mean performing source-code review or debugging source code.

## Normalization Unknowns

When an input is accepted through a fallback path, normalizers should preserve the text representation and add `DocumentInput.metadata.normalization_unknowns` as a list of human-readable uncertainty strings. The pipeline copies these values into `DocumentSummaryState.unknowns` on cache misses so rendered output can expose normalization caveats.
