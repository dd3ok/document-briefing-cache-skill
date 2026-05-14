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
│   ├── evidence.py
│   ├── privacy.py
│   ├── normalize.py
│   ├── summarizers.py
│   ├── render.py
│   ├── pipeline.py
│   ├── cli.py
│   └── templates/
│       ├── brief.md.j2
│       ├── executive.md.j2
│       ├── action_items.md.j2
│       ├── digest.md.j2
│       └── debug.md.j2
├── references/
│   ├── architecture.md
│   ├── schema.md
│   ├── llm-contract.md
│   └── best-practices.md
├── examples/
│   └── mixed_documents.json
├── evals/
│   ├── briefing_eval_cases.json
│   ├── trigger_eval_cases.json
│   └── model_invocation_benchmark_cases.json
├── scripts/
│   └── validate_skill.py
├── tests/
└── docs/
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python >=3.10. If your shell provides `python`, you can use it after the virtual environment is activated.

Optional extras:

```bash
pip install -e ".[llm]"  # OpenAI-backed structured summarizer
pip install -e ".[pdf]"  # PDF text extraction helpers
```

## Input scope

The CLI `--input` option currently accepts local file paths. It does not fetch URLs such as `http://` or `https://`.

URL-bearing metadata inside JSON, XML, HTML, or `DocumentInput.source` is preserved as source/reference metadata for evidence and rendering. To summarize remote content, fetch it outside this tool and pass the saved local file or normalized payload.

## Validate

```bash
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_skill.py --run-evals
```

`--run-evals` executes the compact briefing evals, including structured-state assertions for actions, risks, metrics, and evidence. It also checks trigger evals as static boundary fixtures. Trigger evals validate intended trigger coverage and near-miss cases; they do not measure actual model-side invocation behavior.

`evals/model_invocation_benchmark_cases.json` is a manual benchmark worksheet for hosts that expose real skill invocation telemetry. It is schema-validated, but CI does not claim to measure model-side routing.

Claude.ai description variant: Cache structured briefings for supplied documents, notes, logs, tickets, reports, JSON/XML, or transcripts. Use for repeated summaries, rerendering, digests, actions, risks, or metrics.

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
export DBC_CACHE_HMAC_SECRET="replace-with-a-local-secret"
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --cache-policy ephemeral \
  --no-output-cache \
  --delete-on-exit created \
  --redact-pii \
  --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET
```

For sensitive documents, the safe default is no persistent cache: use `--cache-policy ephemeral --no-output-cache --redact-pii` and add `--delete-on-exit created` when temporary cache files should be removed after the run.

`--redact-pii` applies the built-in `basic-contact-v1` redaction profile before cache misses are summarized, and redacted/non-redacted cache keys are separated. The current profile covers common email addresses, Korean mobile numbers, and US phone numbers. It is not a complete PII detector for names, addresses, national IDs, account numbers, cards, API keys, or access tokens.

`--cache-hmac-secret-env` signs cache envelopes with HMAC-SHA256 using the named environment variable. Signed caches fail closed when the secret is missing and reject payload or expiry metadata tampering. HMAC signing is tamper detection only, not encryption. Use encrypted storage, tmpfs, or another encrypted backend when cache contents need confidentiality.

Cache maintenance commands:

```bash
python -m document_briefing_cache.cli cache stats --cache-dir .cache --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache --older-than 30d --dry-run --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET --json
python -m document_briefing_cache.cli cache clear --cache-dir .cache --layer rendered_outputs --yes
```

When pruning signed caches, pass the same `--cache-hmac-secret-env` used to write them. Without the secret, signed entries are skipped rather than deleted because the CLI cannot distinguish valid signed data from tampered data.

## The default summarizer

The default `rules` summarizer is intentionally deterministic and token-free. It is suitable for:

- demos,
- cache validation,
- shallow digests,
- extracting obvious actions/risks/metrics,
- proving that template rerendering does not require an LLM.

For high-quality summaries of new documents, connect an LLM summarizer at the cache-miss step. Keep the output structured as `DocumentSummaryState`.

OpenAI-backed runs can be configured with explicit model, timeout, retry, and token-budget controls:

```bash
OPENAI_API_KEY="..." python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --summary-mode openai \
  --openai-model gpt-4.1-mini \
  --llm-timeout 60 \
  --llm-max-retries 2 \
  --llm-max-input-tokens 12000 \
  --llm-max-output-tokens 4000 \
  --cache-dir .cache \
  --show-stats
```

When a document exceeds the input budget, the OpenAI adapter summarizes section-based chunks and merges the structured states before writing the document summary cache. Oversized sections are split into smaller text parts while preserving the original section ID for evidence validation. Transient provider failures, including rate limits, server errors, timeouts, and connection-style failures, are retried with exponential backoff; structured-output contract failures are not retried.

Privacy note: `rules` mode is local and token-free. LLM-backed summarizers send cache misses to the configured provider, such as OpenAI, and require the relevant API key. Cache directories are plaintext JSON and may persist structured summaries, names, IDs, dates, metrics, evidence quotes, sources, and rendered outputs. HMAC detects tampering but does not hide contents. Keep `.cache/` out of git, use encrypted storage or tmpfs when needed, and use `ephemeral`, `--redact-pii`, or explicit cache clearing for sensitive documents.

Evidence note: `DocumentSummaryState` schema `1.1.0` requires evidence for the top-level summary and each section digest, in addition to evidence for key points, decisions, actions, risks, and metrics. Evidence quotes should be copied from the normalized source sections so validation can reject unsupported claims and stale `1.0.0` document-summary caches.

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
