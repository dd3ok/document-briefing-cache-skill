# Document Briefing Cache Skill

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/dd3ok/document-briefing-cache-skill)](https://github.com/dd3ok/document-briefing-cache-skill/blob/main/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/dd3ok/document-briefing-cache-skill/ci.yml?branch=main)](https://github.com/dd3ok/document-briefing-cache-skill/actions/workflows/ci.yml)

`document-briefing-cache-skill`은 **AI 에이전트 워크플로우(AI Agent Workflow)**에서 **LLM 토큰 최적화(LLM Token Optimization)**를 위해 설계된 경량 스킬 리포지토리입니다. 방대한 문서를 재사용 가능한 구조화된 브리핑으로 변환하고 캐싱하여, 중복되는 **LLM 호출(LLM Calls)**을 줄이고 **컨텍스트 윈도우 관리(Context Window Management)**를 효율화합니다. 문서의 디지털 지문(fingerprint)을 기반으로 캐시를 관리하여, 한 번 요약된 내용은 포맷 변환이나 반복 요청 시 LLM을 다시 호출할 필요 없이 재사용됩니다. 이는 특히 **LLM 기반 애플리케이션(LLM-powered applications)**의 비용 효율성과 응답 속도를 크게 향상시키는 데 기여합니다.

이 스킬은 다음과 같은 워크플로우를 위해 설계되었습니다:

```text
문서 / JSON / XML / HTML / Markdown / 노트 / 로그 / 보고서
        ↓
DocumentInput으로 정규화
        ↓
문서 지문(fingerprint) 계산
        ↓
캐시된 DocumentSummaryState 재사용 (가능한 경우)
        ↓
캐시 미스(cache misses)만 요약
        ↓
템플릿으로 렌더링
```

목표는 새로운 문서마다 LLM 사용을 없애는 것이 아닙니다. 의미론적 이해가 실제로 필요할 때만 LLM 토큰을 사용하고, 구조화된 결과를 향후 모든 브리핑, 형식 변환 또는 반복 요청에 재사용하는 것입니다.

## What this solves

일반적인 요약 파이프라인은 사용자가 요청할 때마다 LLM을 호출합니다:

```text
"요약해줘" → LLM
"짧게 바꿔줘" → LLM
"Slack용으로 바꿔줘" → LLM
"다시 요약해줘" → LLM
```

이 스킬은 파이프라인을 다음과 같이 변경합니다:

```text
변경된 문서에 대한 첫 요청 → DocumentSummaryState로 요약
반복 요청 → 캐시 히트
형식 변경 → 템플릿 렌더링
다른 대상 → 가능한 경우 템플릿 렌더링
새 문서 추가 → 해당 문서만 요약
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

## Benchmark repeated rendering

Use the benchmark command to measure repeated rendering and incremental-document
cache reuse with a fresh benchmark cache directory:

```bash
python -m document_briefing_cache.cli benchmark \
  --input examples/mixed_documents.json \
  --incremental-input examples/incident_update.json \
  --cache-dir .cache/benchmark-demo \
  --fresh \
  --mode brief \
  --mode digest \
  --mode executive \
  --mode action_items \
  --json
```

For large Markdown-like inputs, add `--split-input-sections` to benchmark
section-level document caching. This is useful when a report is updated by
appending or editing one section: unchanged sections can keep their own
document-summary cache entries instead of invalidating one monolithic document.

The report compares:

- `naive_resummarize_every_run_input_tokens_est`: estimated input tokens if every scenario re-summarized every document.
- `cacheaware_cache_miss_only_input_tokens_est`: estimated input tokens actually sent to the summarizer on document cache misses.
- `summarizer_calls`: cache-miss summarizer calls per scenario.
- `document_cache_hits` / `document_cache_misses`: document-level cache behavior.
- `output_cache_hit`: final rendered-output cache behavior for exact same document set and mode.
- `quality_warning_rows` / `quality_warning_count`: scenarios where the benchmark
  found obvious source candidates that were not present in the structured state.
- `quality_unevaluated_rows`: scenarios served from the rendered-output cache,
  where structured summaries were not reloaded for quality coverage.
- `rows[].quality`: lightweight structural coverage for obvious actions,
  decisions, risks, and metrics. This is not a semantic accuracy score; it helps
  catch cases where token savings hide shallow extraction.

`--fresh` clears only the benchmark cache namespaces under `--cache-dir`
(`document_summaries` and `rendered_outputs`); it does not delete the cache
directory itself or unrelated files beside those namespaces.

Token counts are deterministic estimates from the local benchmark harness, not
provider billing telemetry. For live OpenAI-backed runs, use `--summary-mode
openai` with the same benchmark command and compare provider-side usage or Codex
CLI/OTel telemetry separately.

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
