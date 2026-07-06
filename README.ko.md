# Briefprint

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/dd3ok/briefprint)](https://github.com/dd3ok/briefprint/blob/main/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/dd3ok/briefprint/ci.yml?branch=main)](https://github.com/dd3ok/briefprint/actions/workflows/ci.yml)

한 번 읽고, 어디서든 브리핑하세요.

[English](README.md) | [한국어](README.ko.md)

Briefprint는 반복 문서 브리핑을 위한 `briefprint` 에이전트 스킬과 Python 런타임입니다.

문서를 재사용 가능한 구조화 브리핑으로 바꾸고, 문서 지문으로 캐시한 뒤, 같은 내용을 LLM에 다시 읽히지 않고 새 형식으로 렌더링합니다.

```text
문서형 입력
  -> DocumentInput으로 정규화
  -> 콘텐츠 지문 계산
  -> 캐시 미스만 DocumentSummaryState로 요약
  -> brief / digest / executive / action_items / debug 렌더링
```

## 무엇을 해결하나요?

일반 요약 흐름은 요청이 조금만 바뀌어도 문서를 다시 LLM에 보냅니다.

```text
"요약해줘"        -> LLM이 전체 문서 읽음
"짧게 바꿔줘"    -> LLM이 다시 읽음
"Slack용으로"    -> LLM이 다시 읽음
"업데이트 추가"  -> 전체를 다시 읽을 수 있음
```

Briefprint는 비용이 큰 경계를 바꿉니다. 비싼 작업은 문서 이해이고, 문서가 한 번 `DocumentSummaryState`가 되면 반복 렌더링은 그 상태를 재사용할 수 있습니다.

```text
처음 보는 문서       -> 캐시 미스만 요약
같은 문서 다시 요청  -> 렌더링 출력 캐시 히트
출력 형식만 변경     -> 캐시된 문서 상태에서 템플릿 렌더링
문서 하나만 추가     -> 새 문서만 요약
```

이건 의미 기반 캐시가 아닙니다. 정확한 문서 요약 캐시입니다. 그래서 ID, 날짜, 지표, 장애 로그, 티켓, 보고서처럼 오래되거나 근사한 답이 위험한 작업에 더 안전합니다.

## 빠른 실행

Python 런타임 설치:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.10 이상이 필요합니다. 가상환경 활성화 뒤에는 환경에 따라 `python` 명령을 사용해도 됩니다.

선택 확장:

```bash
pip install -e ".[llm]"  # OpenAI 기반 구조화 요약기
pip install -e ".[pdf]"  # PDF 텍스트 추출 helper
```

이름 안내:

- 에이전트 스킬: `briefprint`
- Python 패키지/CLI: `document-briefing-cache` / `document_briefing_cache`

런타임 이름은 패키지 호환성을 위해 유지하고, 설치 가능한 에이전트 스킬은 Briefprint로 브랜딩합니다.

샘플 실행:

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --mode brief \
  --cache-dir .cache/briefprint \
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
  --cache-dir .cache/briefprint \
  --summary-mode rules \
  --show-stats
```

## 에이전트 스킬 설치

Codex, Claude Code, Gemini CLI, Antigravity, OpenClaw, Hermes 같은 에이전트 호스트에는 가벼운 스킬 번들만 설치하세요.

```text
skills/briefprint/
  SKILL.md
  agents/openai.yaml
  references/*.md
```

repo 루트를 에이전트 스킬로 설치하지 마세요. 루트 복사 방식은 테스트, 문서, 예제, eval, 소스 코드, 검증 스크립트까지 같이 복사할 수 있습니다. 자세한 내용은 [docs/agent-skill-installation.md](docs/agent-skill-installation.md)를 보세요.

Briefprint는 명시 호출형 스킬입니다. Codex에서는 `$briefprint`, Claude Code에서는 `/briefprint`를 사용하고, 그 밖의 호스트에서는 해당 호스트의 명시적 스킬 호출 또는 CLI를 사용하세요. 일반적인 일회성 요약이 자동으로 이 스킬을 트리거해서는 안 됩니다.

Claude.ai description variant: Explicit-use cached briefings for supplied documents, notes, logs, tickets, reports, JSON/XML, or transcripts. Use for repeated summaries, rerendering, digests, actions, risks, or metrics.

## 벤치마크 결과

현재 예제 데이터 기준 로컬 벤치마크 결과입니다. `rules` 요약기를 사용했기 때문에 provider 과금 수치가 아니라 결정적 로컬 추정치입니다.

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

숫자는 솔직하게 봐야 합니다. 이 결과는 로컬 harness의 토큰 추정치입니다. 실제 청구 비용을 보려면 provider usage, Codex CLI/OTel, 또는 사용하는 호스트의 telemetry와 함께 비교해야 합니다. 벤치마크의 품질 체크는 actions, decisions, risks, metrics에 대한 가벼운 smoke check이며 의미론적 정확도 점수는 아닙니다.

## 효과가 큰 경우

- 같은 문서를 여러 번 요약하거나 형식만 바꾸는 경우
- 티켓 묶음, 장애 보고서, 회의록, 로그처럼 재사용되는 문서가 많은 경우
- 기존 문서에 업데이트 하나만 추가되는 경우
- 액션 아이템, 임원 요약, Slack digest, 위험 보고서처럼 출력 목적이 여러 개인 경우

## 효과가 작거나 조심할 경우

- 한 번만 보고 버리는 문서
- 매번 전체 내용이 크게 다시 작성되는 문서
- 섹션 순서나 ID가 계속 바뀌는 문서
- 최신 뉴스, 가격, 정책, 법률처럼 외부 최신성이 중요한 요청

## 입력 범위

현재 CLI의 `--input`은 로컬 파일 경로를 받습니다. `http://` 또는 `https://` URL을 직접 가져오지는 않습니다.

JSON, XML, HTML, `DocumentInput.source` 안에 들어있는 URL 메타데이터는 evidence와 렌더링을 위한 source/reference 정보로 보존됩니다. 원격 문서를 요약하려면 먼저 외부에서 가져와 로컬 파일이나 정규화된 payload로 넘기면 됩니다.

## 모드

| 모드 | 용도 |
|---|---|
| `brief` | 표준 다중 문서 브리핑 |
| `executive` | 의사결정자를 위한 짧은 요약 |
| `action_items` | 담당자, 기한, 후속 작업 중심 |
| `digest` | 채팅 친화적인 짧은 digest |
| `debug` | 파싱된 요약, evidence, 캐시 통계 |

## 캐시와 보안

권장 기본값:

- repo-local 캐시는 `.cache/briefprint` 아래에 두고 Git에는 올리지 않음
- 반복 문서에는 `document_summaries`를 짧은 TTL 캐시로 유지
- 템플릿 렌더링은 싸기 때문에 `rendered_outputs`는 더 짧게 유지
- 평소 실행 때 `--prune-on-start`로 정리
- 민감한 일회성 문서는 `ephemeral` 사용

```bash
python -m document_briefing_cache.cli run \
  --input examples/mixed_documents.json \
  --cache-dir .cache/briefprint \
  --cache-policy ttl \
  --document-ttl 7d \
  --output-ttl 24h \
  --prune-on-start
```

Briefprint는 백그라운드 cleanup daemon을 돌리지 않습니다. TTL은 캐시 항목을 expired로 표시하는 값이고, 실제 파일 삭제는 `cache prune`, `--prune-on-start`, `--prune-on-exit`, delete-on-exit 정책 중 하나가 실행될 때 일어납니다. 이는 로컬 개발 도구에서 흔한 방식입니다. 생성 캐시는 disposable로 보고 Git에서 제외하며, 명시 명령이나 도구 실행 시점에 opportunistic하게 정리합니다. CI 캐시는 예외에 가깝고, GitHub Actions 같은 플랫폼은 자체 last-access/size eviction 정책을 적용합니다.

보존 기간을 길게 잡는 경우는 의도적으로 persistent 캐시를 쓸 때로 제한하세요.

- project-local 기본: `.cache/briefprint`, `--document-ttl 7d`, `--output-ttl 24h`, `--prune-on-start`
- 민감한 일회성 작업: `--sensitive`
- 장기 공유 캐시: 명시적 `--cache-policy persistent` 또는 더 긴 `--document-ttl`

스킬 번들과 runtime cache는 별개입니다. 스킬 번들은 설치 시점의 정적 가이드이고, runtime cache는 `--cache-dir` 아래에 생기며 Briefprint CLI/runtime이 관리합니다. 에이전트 스킬을 설치, 업데이트, 삭제해도 runtime cache가 migrate, prune, delete 되지는 않습니다. 생성된 문서 상태에 대해 모든 agent-skill host가 공통으로 제공하는 portable automatic eviction 계약은 없으므로, 설치된 스킬 디렉터리 안에 문서 캐시를 쓰지 마세요.

민감 문서:

```bash
export DBC_CACHE_HMAC_SECRET="replace-with-a-local-secret"
python -m document_briefing_cache.cli run \
  --input sensitive.json \
  --sensitive \
  --cache-hmac-secret-env DBC_CACHE_HMAC_SECRET
```

민감 문서의 안전한 기본값은 영구 캐시를 남기지 않는 것입니다. `--sensitive`는 `--cache-policy ephemeral --no-output-cache --redact-pii --delete-on-exit created`의 편의 옵션입니다.

`--redact-pii`는 `basic-contact-v1` 프로필을 적용합니다. 이메일, 한국 휴대폰 번호, 미국 전화번호를 다루지만 완전한 PII 탐지기는 아닙니다.

`--redact-secrets`는 `basic-secrets-v1` 프로필을 적용합니다. bearer tokens, API keys, webhook URLs, card-like values, secret-shaped JSON keys를 best-effort로 가립니다. 비밀값 마스킹은 `--sensitive`에 포함되지 않으므로, 민감 문서에 비밀값이 들어갈 수 있으면 별도로 켜야 합니다.

`--redact-secrets`는 `session_id`처럼 운영 상관관계 분석에 쓰이는 값도 secret-shaped key 아래에 있으면 가릴 수 있습니다. 정확한 추적보다 비밀값 보호가 더 중요한 경우에 켜세요.

`--cache-hmac-secret-env`는 HMAC-SHA256으로 캐시 envelope을 서명합니다. HMAC은 tamper detection only, not encryption 입니다. 캐시 내용 자체를 숨겨야 한다면 encrypted storage, tmpfs, 또는 별도 암호화 저장소를 사용해야 합니다.

캐시 관리:

```bash
python -m document_briefing_cache.cli cache stats --cache-dir .cache/briefprint --json
python -m document_briefing_cache.cli cache prune --cache-dir .cache/briefprint --older-than 7d --dry-run --json
python -m document_briefing_cache.cli cache clear --cache-dir .cache/briefprint --layer rendered_outputs --yes
```

## LLM 요약기

기본 `rules` 요약기는 로컬, 결정적, 토큰-free 요약기입니다. 데모, 캐시 검증, 얕은 추출에 적합합니다.

새 문서에 대해 고품질 요약이 필요하면 캐시 미스 단계에 LLM 요약기를 연결하고, 출력은 `DocumentSummaryState` 구조를 유지하세요.

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

주의: LLM 기반 요약기는 캐시 미스 문서를 설정된 provider로 보냅니다. 캐시 디렉터리는 plaintext JSON이며 구조화 요약, 이름, ID, 날짜, 지표, evidence quote, source, 렌더링 결과를 저장할 수 있습니다.

## 검증

```bash
python -m pytest -q
python scripts/validate_skill.py
python scripts/validate_skill.py --run-evals
```

`--run-evals`는 actions, risks, metrics, evidence에 대한 구조화 상태 검증을 실행합니다. `trigger_eval_cases.json`는 static boundary fixtures로 트리거 경계를 점검합니다. 이 fixture는 의도한 트리거와 near-miss를 확인하지만, 실제 모델이 스킬을 호출하는지 여부를 측정하지는 않습니다.

`evals/model_invocation_benchmark_cases.json`는 실제 스킬 호출 telemetry를 제공하는 호스트를 위한 수동 벤치마크 worksheet입니다. schema 검증은 하지만 CI가 모델 측 라우팅을 측정한다고 주장하지는 않습니다.

## repo 구성

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

## 더 읽을 문서

- [README.md](README.md)
- [docs/agent-skill-installation.md](docs/agent-skill-installation.md)
- [references/architecture.md](references/architecture.md)
- [references/schema.md](references/schema.md)
- [references/llm-contract.md](references/llm-contract.md)
- [references/best-practices.md](references/best-practices.md)
- [references/competitive-roadmap.md](references/competitive-roadmap.md)
