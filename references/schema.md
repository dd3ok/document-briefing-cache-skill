# Schema

## DocumentInput

```json
{
  "document_id": "optional stable id",
  "title": "optional title",
  "source": "optional URL/path/source",
  "doc_type": "report | meeting_notes | email | ticket | log | policy | api_payload | news | web_page | transcript | code_review | unknown",
  "content_format": "text | markdown | html | json | xml | pdf_text | unknown",
  "text": "normalized text",
  "raw": "optional original payload",
  "metadata": {}
}
```

## DocumentSummaryState

```json
{
  "schema_version": "1.0.0",
  "document_id": "stable id",
  "content_fingerprint": "sha256",
  "title": "title",
  "source": "source",
  "doc_type": "document type",
  "content_format": "input format",
  "language": "ko | en | unknown",
  "summary": "brief summary",
  "key_points": [{"text": "", "evidence": []}],
  "decisions": [{"text": "", "owner": null, "evidence": []}],
  "actions": [{"action": "", "owner": null, "due": null, "status": "open", "evidence": []}],
  "risks": [{"title": "", "reason": null, "severity": "unknown", "evidence": []}],
  "metrics": [{"name": null, "value": "", "unit": null, "evidence": []}],
  "entities": [],
  "topics": [],
  "open_questions": [],
  "unknowns": [],
  "sections_digest": [],
  "importance": 3,
  "summarizer_id": "rules-extractive-v0.2.0"
}
```

## Design rule

Do not store only the final natural-language paragraph. Store this state, then render paragraphs from it.
