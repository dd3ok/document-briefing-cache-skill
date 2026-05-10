---
name: document-briefing-cache
description: Converts repeated documents, reports, meeting notes, logs, emails, tickets, policies, web pages, news/API JSON/XML, and transcripts into cached structured briefings. Use when the user asks for document summary, briefing, digest, report recap, meeting recap, log review, policy summary, API payload summary, repeated summarization, or template-based rerendering.
---

# Document Briefing Cache Skill

Use this skill when structured or semi-structured content should be summarized once and reused many times without repeatedly spending LLM tokens.

## Core idea

Do not treat every briefing request as a fresh LLM summarization task.

Prefer this order:

1. Normalize every input into `DocumentInput`.
2. Compute a stable `content_fingerprint` for each document.
3. Reuse a cached `DocumentSummaryState` when the document fingerprint and summarizer contract match.
4. Render the final output from templates.
5. Use an LLM only for cache misses or for genuinely new reasoning that cannot be produced from cached state.

## Inputs this skill can handle

- Plain text
- Markdown
- HTML pages
- XML
- JSON API payloads
- Meeting notes
- Reports
- Emails
- Tickets and issue updates
- Incident and system logs
- Policies and manuals
- News articles
- Transcripts
- Any document-like payload that can be normalized to text and metadata

## Canonical state

Every document should become this durable state:

```json
{
  "schema_version": "1.0.0",
  "document_id": "stable id",
  "content_fingerprint": "sha256 hash",
  "title": "document title",
  "source": "optional source or URL",
  "doc_type": "report | meeting_notes | email | ticket | log | policy | api_payload | news | web_page | transcript | unknown",
  "summary": "short meaning-preserving summary",
  "key_points": [],
  "decisions": [],
  "actions": [],
  "risks": [],
  "metrics": [],
  "entities": [],
  "topics": [],
  "open_questions": [],
  "unknowns": []
}
```

## Rules

- Preserve dates, numbers, names, IDs, URLs, and source references exactly.
- Never invent missing values. Put missing or ambiguous items in `unknowns` or `open_questions`.
- Cache at the document level, not only at the final briefing level.
- If the same document appears again, do not summarize it again.
- If only the output format changes, do not call the LLM.
- If only the audience changes and the requested output can be rendered from existing fields, do not call the LLM.
- If a document has changed, only reprocess that document.
- Keep LLM output structured as `DocumentSummaryState`, not as one final paragraph.
- Use templates for Markdown, Slack, email, executive, action-item, and debug renderings.

## When to call an LLM

Call an LLM only when at least one of these is true:

- The document fingerprint is new and no cached `DocumentSummaryState` exists.
- The user asks for interpretation that is not present in cached fields.
- The document contains ambiguous, conflicting, or highly domain-specific meaning.
- The user requests new synthesis across multiple documents that cannot be derived deterministically.

## When not to call an LLM

Do not call an LLM for:

- Same document, same summarizer contract.
- Same document set, same output mode.
- Format conversion: brief → Slack → executive → email.
- Simple ordering, filtering, grouping, or deduplication.
- Rendering action items, risks, decisions, or metrics already stored in state.
- Debug output that shows parsed state and cache keys.

## Rendering modes

- `brief`: standard multi-document briefing
- `executive`: concise decision-maker version
- `action_items`: actions, owners, due dates, and open questions
- `digest`: short digest for chat or Slack
- `debug`: cache and parsed-state visibility

## Success criteria

- Re-running the same input should produce `summarizer_calls = 0`.
- Changing only the rendering mode should produce `summarizer_calls = 0`.
- Adding one new document should summarize only that document.
- Numbers, dates, IDs, and source references should remain unchanged.
- The final answer should be generated from cached structured state whenever possible.
