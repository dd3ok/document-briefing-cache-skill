# Architecture

The skill is intentionally small and has five stages.

```text
normalize → fingerprint → cache → summarize cache misses → render
```

## 1. Normalize

All inputs become `DocumentInput`:

- `title`
- `source`
- `doc_type`
- `content_format`
- `text`
- `raw`
- `metadata`

The normalizer supports JSON, XML, HTML, Markdown, text, and optional PDF text extraction.

## 2. Fingerprint

A document fingerprint is generated from normalized content, source, title, type, and format. This allows the pipeline to detect repeated documents.

## 3. Cache

The skill uses two cache layers by default:

- `document_summaries`: stores `DocumentSummaryState`
- `rendered_outputs`: stores final rendered strings

Document-level cache is more important than final-output cache because it allows adding one new document without re-summarizing all previous documents.

## 4. Summarize

The default summarizer is rule-based and token-free. It is not meant to be as good as an LLM. It exists to make the pipeline deterministic and testable.

In production, replace or wrap `BaseSummarizer` with an LLM summarizer that emits `DocumentSummaryState`.

## 5. Render

Templates turn the structured state into briefings:

- `brief`
- `executive`
- `action_items`
- `digest`
- `debug`

Changing the template should not trigger summarization.
