# Briefprint

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/dd3ok/briefprint)](https://github.com/dd3ok/briefprint/blob/main/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/dd3ok/briefprint/ci.yml?branch=main)](https://github.com/dd3ok/briefprint/actions/workflows/ci.yml)

Read once. Brief anywhere.

[English](README.md) | [한국어](README.ko.md)

Briefprint packages the `briefprint` agent skill and Python runtime for repeated document briefing work.

It turns documents into reusable structured briefings, caches them by document fingerprint, and renders new formats from the cached state instead of asking an LLM to re-read the same content.

```text
document-like input
  -> normalize to DocumentInput
  -> fingerprint the content
  -> summarize cache misses into DocumentSummaryState
  -> render brief / digest / executive / action items / debug
```

## What It Solves

Most summarization workflows pay again every time the user asks for a slightly different answer.

```text
"summarize this"          -> LLM reads the whole document
"make it shorter"        -> LLM reads the whole document again
"make it Slack-friendly" -> LLM reads the whole document again
"add this one update"    -> LLM may read everything again
```

Briefprint changes the boundary. The expensive step is document understanding. Once a document has a `DocumentSummaryState`, repeated render requests can reuse it.

```text
first run on changed documents -> summarize cache misses
same document set              -> rendered-output cache hit
new render mode                -> template render from cached document state
one new update                 -> summarize only the new document
```

This is not a semantic cache. It is an exact document-summary cache, which is safer for IDs, dates, metrics, incident logs, tickets, and reports where stale or approximate answers are unacceptable.

## Quick Start

Install the Python runtime:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python >=3.10. If your shell provides `python`, use it after the virtual environment is activated.

Optional extras:

```bash
pip install -e ".[llm]"  # OpenAI-backed structured summarizer
pip install -e ".[pdf]"  # PDF text extraction helpers
```

Naming note:

- Agent skill: `briefprint`
- Python package/CLI: `document-briefing-cache` / `document_briefing_cache`

The runtime names are kept for package compatibility while the installable agent skill is branded as Briefprint.

Run the sample:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode brief \
  --cache-dir .cache/briefprint \
  --summary-mode rules \
  --show-stats \
  --explain-cache
```

Run the same command again. Repeated content should not call the summarizer:

```text
summarizer_calls: 0
```

Render another format from the same cached document state:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode action_items \
  --cache-dir .cache/briefprint \
  --summary-mode rules \
  --show-stats
```

## Agent Skill Install

For Codex, Claude Code, Gemini CLI, Antigravity, OpenClaw, Hermes, or another agent host, install only the lightweight skill bundle:

```text
skills/briefprint/
  SKILL.md
  agents/openai.yaml
  references/*.md
```

Do not install the repository root as an agent skill. Root-copy installers can include tests, docs, examples, evals, source code, and validation scripts. See [docs/agent-skill-installation.md](docs/agent-skill-installation.md).

Briefprint is explicit-use by design. For Codex, use `$briefprint`; for Claude Code, use `/briefprint`; for other hosts, use the host's explicit skill invocation or the CLI when you want reusable cached document briefings. Ordinary one-off summaries should not trigger the skill automatically.

Claude.ai description variant: Explicit-use cached briefings for supplied documents, notes, logs, tickets, reports, JSON/XML, or transcripts. Use for repeated summaries, rerendering, digests, actions, risks, or metrics.

## Benchmark Receipts

This local benchmark was run on the current examples with the deterministic `rules` summarizer:

```bash
python -m document_briefing_cache.cli benchmark \
  --input examples/mixed_documents.json \
  --incremental-input examples/incident_update.json \
  --cache-dir .cache/briefprint/readme-benchmark \
  --fresh \
  --mode brief \
  --mode digest \
  --mode executive \
  --mode action_items \
  --json
```

| Measure | Result |
|---|---:|
| Scenarios | 7 |
| Base documents | 3 |
| Combined documents after update | 4 |
| Naive re-summarization input tokens estimate | 1,748 |
| Cache-aware cache-miss input tokens estimate | 309 |
| Estimated tokens saved | 1,439 |
| Estimated savings | 82.32% |
| Total summarizer calls | 4 |
| Document cache hits | 16 |
| Document cache misses | 4 |

Scenario shape:

| Scenario | Summarizer calls | Cache-miss input tokens |
|---|---:|---:|
| Cold brief over 3 documents | 3 | 226 |
| Same brief again | 0 | 0 |
| Rerender digest | 0 | 0 |
| Rerender executive | 0 | 0 |
| Rerender action items | 0 | 0 |
| Add one update | 1 | 83 |
| Rerender debug over combined set | 0 | 0 |

Rows with `0` summarizer calls and `0` cache-miss input tokens are intentional: they show that rerenders and repeated briefs reuse cached structured state instead of re-reading unchanged documents.

Honest number warning: these are deterministic local estimates from the benchmark harness, not provider billing telemetry. Use OpenAI/provider usage or host telemetry when exact billing matters. The benchmark also includes lightweight quality smoke checks for obvious actions, decisions, risks, and metrics; it is not a semantic accuracy score.

## When It Helps

- Repeated briefs over the same tickets, incident reports, meeting notes, logs, or PR summaries.
- Rendering one source into several outputs: executive memo, Slack digest, action list, risk report, debug view.
- Incremental feeds where one new item is appended and older items keep stable IDs.
- Agent workflows where the same source needs to be reused across several turns.

## When It Does Not Help Much

- One-off documents that will never be reused.
- Documents that are rewritten wholesale each time.
- Inputs with unstable section IDs or reordered sections, unless you pass structured records with stable IDs.
- Requests that require fresh external facts, policy changes, current prices, or live news.

## Input Scope

The CLI `--input` option currently accepts local file path values. It does not fetch URLs such as `http://` or `https://`.

URL-bearing metadata inside JSON, XML, HTML, or `DocumentInput.source` is preserved as source/reference metadata for evidence and rendering. To summarize remote content, fetch it outside this tool and pass the saved local file or normalized payload.

## Modes

| Mode | Use |
|---|---|
| `brief` | Standard multi-document briefing |
| `executive` | Concise decision-maker summary |
| `action_items` | Owners, deadlines, follow-ups |
| `digest` | Chat-friendly short digest |
| `debug` | Parsed summaries, evidence, and cache stats |

## Cache And Privacy

Recommended defaults:

- keep repo-local cache under `.cache/briefprint` and keep it out of version control,
- keep `document_summaries` as a short TTL cache for repeated documents,
- keep `rendered_outputs` shorter-lived because template rendering is cheap,
- run pruning during normal use with `--prune-on-start`,
- use `ephemeral` for sensitive one-off work.

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --cache-dir .cache/briefprint \
  --cache-policy ttl \
  --document-ttl 7d \
  --output-ttl 24h \
  --prune-on-start
```

Briefprint does not run a background cleanup daemon. TTL values mark cache entries as expired; physical deletion happens when you run `cache prune`, enable `--prune-on-start` or `--prune-on-exit`, or use a delete-on-exit policy. This follows the common local-tooling pattern: generated caches are disposable, ignored by Git, and cleaned explicitly or opportunistically during tool runs. CI caches are the main exception; platforms such as GitHub Actions apply their own last-access and size eviction policies.

Use longer retention only when the cache is intentionally persistent:

- project-local default: `.cache/briefprint`, `--document-ttl 7d`, `--output-ttl 24h`, `--prune-on-start`,
- sensitive one-off work: `--sensitive`,
- long-lived shared cache: explicit `--cache-policy persistent` or a longer `--document-ttl`.

Skill bundle and runtime cache are separate. The skill bundle is static install-time guidance; the runtime cache lives under `--cache-dir` and is owned by the Briefprint CLI/runtime. Installing, updating, or removing the agent skill does not migrate, prune, or delete runtime caches. No portable agent-skill host contract currently provides automatic eviction for generated document state, so do not write document caches into the installed skill directory.

For sensitive documents:

```bash
export DBC_CACHE_HMAC_SECRET="replace-with-a-local-secret"
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --sensitive \
  --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET
```

For sensitive documents, the safe default is no persistent cache. `--sensitive` is a convenience alias for `--cache-policy ephemeral --no-output-cache --redact-pii --delete-on-exit created`.

`--redact-pii` applies the built-in `basic-contact-v1` profile before cache misses are summarized. It covers common email addresses, Korean mobile numbers, and US phone numbers. It is not a complete PII detector.

`--redact-secrets` applies the built-in `basic-secrets-v1` profile. It is best-effort and targets bearer tokens, API keys, webhook URLs, card-like values, and string values under secret-shaped JSON keys. Secret redaction is not included in --sensitive; enable it explicitly when secret-shaped values may appear.

`--redact-secrets` may also remove operational correlation values such as `session_id` when they appear under secret-shaped keys. Enable it when secret protection matters more than exact operational correlation.

`--cache-hmac-secret-env` signs cache envelopes with HMAC-SHA256. HMAC is tamper detection only, not encryption. Use encrypted storage, tmpfs, or another encrypted backend when cache contents need confidentiality.

Cache maintenance:

```bash
python -m document_briefing_cache.cli cache stats --cache-dir .cache/briefprint --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache/briefprint --older-than 7d --dry-run --json
python -m document_briefing_cache.cli cache clear --cache-dir .cache/briefprint --layer rendered_outputs --yes
```

## LLM Summarizer

The default `rules` summarizer is local, deterministic, and token-free. It is useful for demos, cache validation, and shallow extraction.

For high-quality summaries of new documents, connect an LLM summarizer at the cache-miss step and keep the output structured as `DocumentSummaryState`.

```bash
OPENAI_API_KEY="..." python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --summary-mode openai \
  --openai-model gpt-4.1-mini \
  --llm-timeout 60 \
  --llm-max-retries 2 \
  --llm-max-input-tokens 12000 \
  --llm-max-output-tokens 4000 \
  --cache-dir .cache/briefprint \
  --show-stats
```

Privacy note: LLM-backed summarizers send cache misses to the configured provider. Cache directories are plaintext JSON and may persist structured summaries, names, IDs, dates, metrics, evidence quotes, sources, and rendered outputs.

## Validate

```bash
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_skill.py --run-evals
```

`--run-evals` executes compact briefing evals with structured-state assertions for actions, risks, metrics, and evidence. It also checks `trigger_eval_cases.json` as static boundary fixtures. Trigger evals validate intended trigger coverage and near-miss cases; they do not measure actual model-side invocation behavior.

`evals/model_invocation_benchmark_cases.json` is a manual benchmark worksheet for hosts that expose real skill invocation telemetry. It is schema-validated, but CI does not claim to measure model-side routing.

## Repository Map

```text
skills/briefprint/                 installable agent skill
src/document_briefing_cache/        Python runtime and CLI
src/document_briefing_cache/templates/
                                    render templates
examples/                           sample inputs and demos
evals/                              compact eval and benchmark fixtures
references/                         architecture, schema, LLM contract, roadmap
docs/agent-skill-installation.md     host-specific install notes
tests/                              unit and behavior tests
scripts/validate_skill.py           repository validation
```

## Further Reading

- [README.ko.md](README.ko.md)
- [docs/agent-skill-installation.md](docs/agent-skill-installation.md)
- [references/architecture.md](references/architecture.md)
- [references/schema.md](references/schema.md)
- [references/llm-contract.md](references/llm-contract.md)
- [references/best-practices.md](references/best-practices.md)
- [references/competitive-roadmap.md](references/competitive-roadmap.md)
