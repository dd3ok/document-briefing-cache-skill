# Briefprint

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/dd3ok/briefprint)](https://github.com/dd3ok/briefprint/blob/main/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/dd3ok/briefprint/ci.yml?branch=main)](https://github.com/dd3ok/briefprint/actions/workflows/ci.yml)

Read once. Brief anywhere.

[English](#english) | [한국어](#korean)

Briefprint packages the `briefprint` agent skill and Python runtime for repeated document briefing work.

It turns documents into reusable structured briefings, caches them by document fingerprint, and renders new formats from the cached state instead of asking an LLM to re-read the same content.

```text
document-like input
  -> normalize to DocumentInput
  -> fingerprint the content
  -> summarize cache misses into DocumentSummaryState
  -> render brief / digest / executive / action items / debug
```

## English

### What It Solves

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

### Quick Start

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

Run the sample:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode brief \
  --cache-dir .cache \
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
  --cache-dir .cache \
  --summary-mode rules \
  --show-stats
```

### Agent Skill Install

For Codex, Claude Code, Gemini CLI, Antigravity, OpenClaw, Hermes, or another agent host, install only the lightweight skill bundle:

```text
skills/briefprint/
  SKILL.md
  agents/openai.yaml
  references/*.md
```

Do not install the repository root as an agent skill. Root-copy installers can include tests, docs, examples, evals, source code, and validation scripts. See [docs/agent-skill-installation.md](docs/agent-skill-installation.md).

Claude.ai description variant: Cache structured briefings for supplied documents, notes, logs, tickets, reports, JSON/XML, or transcripts. Use for repeated summaries, rerendering, digests, actions, risks, or metrics.

### Benchmark Receipts

This local benchmark was run on the current examples with the deterministic `rules` summarizer:

```bash
python -m document_briefing_cache.cli benchmark \
  --input examples/mixed_documents.json \
  --incremental-input examples/incident_update.json \
  --cache-dir .cache/readme-benchmark \
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
| Quality warning rows | 0 |

Scenario shape:

| Scenario | Summarizer calls | Cache-aware input tokens |
|---|---:|---:|
| Cold brief over 3 documents | 3 | 226 |
| Same brief again | 0 | 0 |
| Rerender digest | 0 | 0 |
| Rerender executive | 0 | 0 |
| Rerender action items | 0 | 0 |
| Add one update | 1 | 83 |
| Rerender debug over combined set | 0 | 0 |

Honest number warning: these are deterministic local estimates from the benchmark harness, not provider billing telemetry. Use OpenAI/provider usage or host telemetry when exact billing matters. The benchmark also includes lightweight quality smoke checks for obvious actions, decisions, risks, and metrics; it is not a semantic accuracy score.

### When It Helps

- Repeated briefs over the same tickets, incident reports, meeting notes, logs, or PR summaries.
- Rendering one source into several outputs: executive memo, Slack digest, action list, risk report, debug view.
- Incremental feeds where one new item is appended and older items keep stable IDs.
- Agent workflows where the same source needs to be reused across several turns.

### When It Does Not Help Much

- One-off documents that will never be reused.
- Documents that are rewritten wholesale each time.
- Inputs with unstable section IDs or reordered sections, unless you pass structured records with stable IDs.
- Requests that require fresh external facts, policy changes, current prices, or live news.

### Input Scope

The CLI `--input` option currently accepts local file path values. It does not fetch URLs such as `http://` or `https://`.

URL-bearing metadata inside JSON, XML, HTML, or `DocumentInput.source` is preserved as source/reference metadata for evidence and rendering. To summarize remote content, fetch it outside this tool and pass the saved local file or normalized payload.

### Modes

| Mode | Use |
|---|---|
| `brief` | Standard multi-document briefing |
| `executive` | Concise decision-maker summary |
| `action_items` | Owners, deadlines, follow-ups |
| `digest` | Chat-friendly short digest |
| `debug` | Parsed summaries, evidence, and cache stats |

### Cache And Privacy

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
  --sensitive \
  --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET
```

For sensitive documents, the safe default is no persistent cache. `--sensitive` is a convenience alias for `--cache-policy ephemeral --no-output-cache --redact-pii --delete-on-exit created`.

`--redact-pii` applies the built-in `basic-contact-v1` profile before cache misses are summarized. It covers common email addresses, Korean mobile numbers, and US phone numbers. It is not a complete PII detector.

`--redact-secrets` applies the built-in `basic-secrets-v1` profile. It is best-effort and targets bearer tokens, API keys, webhook URLs, card-like values, and string values under secret-shaped JSON keys. Secret redaction is not included in --sensitive; enable it explicitly when secret-shaped values may appear.

`--cache-hmac-secret-env` signs cache envelopes with HMAC-SHA256. HMAC is tamper detection only, not encryption. Use encrypted storage, tmpfs, or another encrypted backend when cache contents need confidentiality.

Cache maintenance:

```bash
python -m document_briefing_cache.cli cache stats --cache-dir .cache --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache --older-than 30d --dry-run --json
python -m document_briefing_cache.cli cache clear --cache-dir .cache --layer rendered_outputs --yes
```

### LLM Summarizer

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
  --cache-dir .cache \
  --show-stats
```

Privacy note: LLM-backed summarizers send cache misses to the configured provider. Cache directories are plaintext JSON and may persist structured summaries, names, IDs, dates, metrics, evidence quotes, sources, and rendered outputs.

### Validate

```bash
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_skill.py --run-evals
```

`--run-evals` executes compact briefing evals with structured-state assertions for actions, risks, metrics, and evidence. It also checks `trigger_eval_cases.json` as static boundary fixtures. Trigger evals validate intended trigger coverage and near-miss cases; they do not measure actual model-side invocation behavior.

`evals/model_invocation_benchmark_cases.json` is a manual benchmark worksheet for hosts that expose real skill invocation telemetry. It is schema-validated, but CI does not claim to measure model-side routing.

### Repository Map

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

<a id="korean"></a>

## 한국어

### 무엇인가요?

Briefprint는 반복 문서 브리핑을 위한 경량 에이전트 스킬과 Python 런타임입니다. 한 번 읽은 문서를 `DocumentSummaryState`라는 구조화 상태로 저장하고, 이후에는 같은 문서를 다시 요약하지 않고 여러 형식으로 렌더링합니다.

쉽게 말하면:

```text
문서 읽기와 이해는 비싼 작업
형식 바꾸기는 싼 작업

비싼 작업은 캐시 미스 때만 하고,
반복 요청은 캐시된 구조화 결과로 처리합니다.
```

### 해결하려는 문제

일반 요약 흐름은 요청이 조금만 바뀌어도 문서를 다시 LLM에 보냅니다.

```text
"요약해줘"        -> LLM이 전체 문서 읽음
"짧게 바꿔줘"    -> LLM이 다시 읽음
"Slack용으로"    -> LLM이 다시 읽음
"업데이트 추가"  -> 전체를 다시 읽을 수 있음
```

Briefprint는 문서별 지문을 기준으로 캐시합니다.

```text
처음 보는 문서       -> 요약 후 DocumentSummaryState 저장
같은 문서 다시 요청  -> 캐시 사용
출력 형식만 변경     -> 템플릿 렌더링
문서 하나만 추가     -> 새 문서만 요약
```

그래서 티켓, 장애 보고서, 회의록, 로그, PR 요약처럼 같은 원문을 여러 번 재사용하는 업무에 적합합니다.

### 빠른 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

선택 확장:

```bash
pip install -e ".[llm]"  # OpenAI 기반 구조화 요약기
pip install -e ".[pdf]"  # PDF 텍스트 추출 helper
```

샘플 실행:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode brief \
  --cache-dir .cache \
  --summary-mode rules \
  --show-stats \
  --explain-cache
```

같은 명령을 다시 실행하면 반복 문서에 대해서는 요약 호출이 없어야 합니다.

```text
summarizer_calls: 0
```

같은 문서를 액션 아이템 형식으로 다시 렌더링:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode action_items \
  --cache-dir .cache \
  --summary-mode rules \
  --show-stats
```

### 에이전트 스킬 설치

에이전트에 설치할 때는 repo 전체가 아니라 아래 폴더만 설치합니다.

```text
skills/briefprint/
```

이 폴더에는 스킬 실행에 필요한 `SKILL.md`, `agents/openai.yaml`, `references/*.md`만 들어갑니다. repo 루트를 스킬로 설치하면 테스트, 문서, 예제, eval, 소스 코드, 검증 스크립트까지 같이 들어갈 수 있으므로 피해야 합니다.

자세한 설치 경로는 [docs/agent-skill-installation.md](docs/agent-skill-installation.md)를 보세요.

### 벤치마크 결과

현재 예제 데이터 기준 로컬 벤치마크 결과입니다. `rules` 요약기를 사용했기 때문에 provider 과금 수치가 아니라 결정적 로컬 추정치입니다.

| 항목 | 결과 |
|---|---:|
| 시나리오 | 7 |
| 기본 문서 | 3 |
| 업데이트 후 문서 | 4 |
| 매번 다시 요약할 때 입력 토큰 추정 | 1,748 |
| 캐시 미스만 요약할 때 입력 토큰 추정 | 309 |
| 절약 추정 토큰 | 1,439 |
| 절약률 | 82.32% |
| 총 요약 호출 | 4 |
| 문서 캐시 히트 | 16 |
| 문서 캐시 미스 | 4 |
| 품질 경고 행 | 0 |

시나리오별 핵심 결과:

| 시나리오 | 요약 호출 | 캐시 인식 입력 토큰 |
|---|---:|---:|
| 문서 3개 최초 브리핑 | 3 | 226 |
| 같은 브리핑 반복 | 0 | 0 |
| digest로 재렌더링 | 0 | 0 |
| executive로 재렌더링 | 0 | 0 |
| action_items로 재렌더링 | 0 | 0 |
| 업데이트 1개 추가 | 1 | 83 |
| 합쳐진 문서 debug 렌더링 | 0 | 0 |

숫자는 솔직하게 봐야 합니다. 이 결과는 로컬 harness의 토큰 추정치입니다. 실제 청구 비용을 보려면 provider usage, Codex CLI/OTel, 또는 사용하는 호스트의 telemetry와 함께 비교해야 합니다.

### 효과가 큰 경우

- 같은 문서를 여러 번 요약하거나 형식만 바꾸는 경우
- 티켓 묶음, 장애 보고서, 회의록, 로그처럼 재사용되는 문서가 많은 경우
- 기존 문서에 업데이트 하나만 추가되는 경우
- 액션 아이템, 임원 요약, Slack digest, 위험 보고서처럼 출력 목적이 여러 개인 경우

### 효과가 작거나 조심할 경우

- 한 번만 보고 버리는 문서
- 매번 전체 내용이 크게 다시 작성되는 문서
- 섹션 순서나 ID가 계속 바뀌는 문서
- 최신 뉴스, 가격, 정책, 법률처럼 외부 최신성이 중요한 요청

### 입력 범위

현재 CLI의 `--input`은 로컬 파일 경로를 받습니다. `http://` 또는 `https://` URL을 직접 가져오지는 않습니다.

JSON, XML, HTML, `DocumentInput.source` 안에 들어있는 URL 메타데이터는 evidence와 렌더링을 위한 source/reference 정보로 보존됩니다. 원격 문서를 요약하려면 먼저 외부에서 가져와 로컬 파일이나 정규화된 payload로 넘기면 됩니다.

### 캐시와 보안

민감 문서에는 기본적으로 영구 캐시를 남기지 않는 흐름을 권장합니다.

```bash
export DBC_CACHE_HMAC_SECRET="replace-with-a-local-secret"
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --sensitive \
  --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET
```

`--sensitive`는 `--cache-policy ephemeral --no-output-cache --redact-pii --delete-on-exit created`의 편의 옵션입니다.

`--redact-pii`는 `basic-contact-v1` 프로필을 적용합니다. 이메일, 한국 휴대폰 번호, 미국 전화번호를 다루지만 완전한 PII 탐지기는 아닙니다.

`--redact-secrets`는 `basic-secrets-v1` 프로필을 적용합니다. bearer tokens, API keys, webhook URLs, card-like values, secret-shaped JSON keys를 best-effort로 가립니다. Secret redaction is not included in --sensitive; 민감 문서에 비밀값이 들어갈 수 있으면 별도로 켜야 합니다.

HMAC 서명은 tamper detection only, not encryption 입니다. 캐시 내용 자체를 숨겨야 한다면 encrypted storage, tmpfs, 또는 별도 암호화 저장소를 사용해야 합니다.

### 검증

```bash
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_skill.py --run-evals
```

`--run-evals`는 actions, risks, metrics, evidence에 대한 구조화 상태 검증을 실행합니다. `trigger_eval_cases.json`는 static boundary fixtures로 트리거 경계를 점검합니다. 이 fixture는 의도한 트리거와 near-miss를 확인하지만, 실제 모델이 스킬을 호출하는지 여부를 측정하지는 않습니다.

### repo 구성

```text
skills/briefprint/                 설치 가능한 에이전트 스킬
src/document_briefing_cache/        Python 런타임과 CLI
src/document_briefing_cache/templates/
                                    출력 템플릿
examples/                           샘플 입력과 데모
evals/                              eval 및 벤치마크 fixture
references/                         아키텍처, 스키마, LLM 계약, 로드맵
docs/agent-skill-installation.md     호스트별 설치 문서
tests/                              테스트
scripts/validate_skill.py           repo 검증 스크립트
```

### 더 읽을 문서

- [references/architecture.md](references/architecture.md)
- [references/schema.md](references/schema.md)
- [references/llm-contract.md](references/llm-contract.md)
- [references/best-practices.md](references/best-practices.md)
- [references/competitive-roadmap.md](references/competitive-roadmap.md)
