# Document Briefing Cache Skill

A lightweight skill repository for turning broad documents into reusable structured briefings.

It is designed for this workflow:

```text
Document / JSON / XML / HTML / Markdown / notes / logs / reports
        ↓
Normalize to DocumentInput
        ↓
Compute document fingerprint
        ↓
Reuse cached DocumentSummaryState if available
        ↓
Summarize only cache misses
        ↓
Render with templates
```

The goal is not to make LLM usage disappear for every new document. The goal is to spend LLM tokens only when semantic understanding is actually required, then reuse the structured result for every future briefing, format conversion, or repeated request.

## What this solves

Typical summarization pipelines call an LLM every time the user asks:

```text
"요약해줘" → LLM
"짧게 바꿔줘" → LLM
"Slack용으로 바꿔줘" → LLM
"다시 요약해줘" → LLM
```

This skill changes the pipeline to:

```text
First time for a changed document → summarize into DocumentSummaryState
Repeated request → cache hit
Format change → template render
Different audience → template render when possible
Only new document added → summarize only that document
```

## Repository layout

```text
.
├── SKILL.md
├── README.md
├── AGENTS.md
├── VALIDATION.md
├── pyproject.toml
├── agents/
│   └── openai.yaml
├── src/document_briefing_cache/
│   ├── models.py
│   ├── hashing.py
│   ├── cache.py
│   ├── normalize.py
│   ├── summarizers.py
│   ├── render.py
│   ├── pipeline.py
│   └── cli.py
├── templates/
│   ├── brief.md.j2
│   ├── executive.md.j2
│   ├── action_items.md.j2
│   ├── digest.md.j2
│   └── debug.md.j2
├── references/
│   ├── architecture.md
│   ├── schema.md
│   ├── llm-contract.md
│   └── best-practices.md
├── examples/
│   └── mixed_documents.json
├── scripts/
│   └── validate_skill.py
└── tests/
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Validate

```bash
pytest -q
python scripts/validate_skill.py
```

## Run the sample

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode brief \
  --cache-dir .cache \
  --summary-mode rules \
  --show-stats
```

Run the same command again. You should see no summarizer calls for repeated content.

```text
summarizer_calls: 0
```

Try a different template without re-summarizing:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode action_items \
  --cache-dir .cache \
  --summary-mode rules \
  --show-stats
```

## Modes

- `brief`: standard multi-document briefing
- `executive`: concise decision-maker summary
- `action_items`: action-focused rendering
- `digest`: chat-friendly short digest
- `debug`: parsed summaries and cache stats

## Cache lifecycle

The cache can now be kept, expired, or deleted after a run.

Recommended defaults:

- keep `document_summaries` as a TTL cache for repeated documents,
- keep `rendered_outputs` short-lived because template rendering is cheap,
- use `ephemeral` for sensitive one-off work.

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --cache-policy ttl \
  --document-ttl 30d \
  --output-ttl 24h \
  --prune-on-start
```

For sensitive documents:

```bash
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --cache-policy ephemeral
```

Cache maintenance commands:

```bash
python -m document_briefing_cache.cli cache stats --cache-dir .cache --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache --older-than 30d --dry-run --json
python -m document_briefing_cache.cli cache clear --cache-dir .cache --layer rendered_outputs --yes
```

## The default summarizer

The default `rules` summarizer is intentionally deterministic and token-free. It is suitable for:

- demos,
- cache validation,
- shallow digests,
- extracting obvious actions/risks/metrics,
- proving that template rerendering does not require an LLM.

For high-quality summaries of new documents, connect an LLM summarizer at the cache-miss step. Keep the output structured as `DocumentSummaryState`.

## Recommended production design

```text
L1 output cache
  Same document set + same render mode → return final string

L2 document summary cache
  Same document fingerprint + same summarizer contract → reuse DocumentSummaryState

L3 provider prompt cache
  Repeated system instructions, schema, and examples stay stable

L4 optional semantic cache
  Use only for safe, non-time-sensitive, non-numeric repeated questions
```

Avoid using semantic cache for data-sensitive requests such as current metrics, legal/policy changes, financial figures, or time-bound news.

## Why store structured state instead of final paragraphs?

A final paragraph is hard to reuse. Structured state can be rendered into many outputs:

```text
DocumentSummaryState
  ├── Markdown briefing
  ├── Slack digest
  ├── executive memo
  ├── action item list
  ├── risk report
  └── debug/citation view
```

That is the core reason this skill caches `DocumentSummaryState`, not just text.
