# Competitive Roadmap

Status: proposed  
Last reviewed: 2026-07-03  
Scope: lightweight roadmap for keeping this repository a compact exact-cache document briefing skill.

## Position

The repository should stay narrow:

```text
Cache document meaning once. Rerender briefs, digests, actions, risks, and metrics without re-summarizing unchanged documents.
```

The competitive wedge is not a broader document platform, RAG system, semantic cache, crawler, or dashboard. The wedge is a small skill that can prove four claims:

1. Unchanged documents do not call the summarizer again.
2. Template-only changes render from cached structured state.
3. Adding one new document summarizes only that document.
4. Rendered claims are evidence-backed, or gaps are visible as warnings or unknowns.

Every roadmap item should strengthen one of those claims without making `SKILL.md` or the runtime surface heavy.

## Evidence Reviewed

Repository evidence:

- `SKILL.md`: exact-cache workflow and safety rules.
- `README.md`: benchmark command, production design, privacy notes, provider-cache positioning.
- `src/document_briefing_cache/pipeline.py`: output cache, document cache, cache keys, summarizer calls, evidence validation.
- `src/document_briefing_cache/hashing.py`: exact fingerprints and cache keys.
- `src/document_briefing_cache/models.py`: `DocumentInput`, `DocumentSummaryState`, `PipelineStats`.
- `src/document_briefing_cache/normalize.py`: JSON record normalization and section-level splitting.
- `src/document_briefing_cache/benchmark.py`: local cache-aware token estimates and structural quality warnings.
- `references/best-practices.md`: exact-cache guidance, semantic-cache limits, provider prompt caching as secondary optimization.
- `evals/briefing_eval_cases.json`: existing cache reuse and structured-state fixtures.

External guidance:

- OpenAI and Codex skills guidance supports compact `SKILL.md`, trigger-focused descriptions, and supporting files for longer reference material.
- Claude Code skills guidance also supports compact `SKILL.md` and moving long examples or references out of the skill body.
- OpenAI prompt caching guidance supports treating provider prompt caching as prefix-processing optimization with `cached_tokens`, not as application-level document state reuse.

Important boundary: vendor docs support the packaging principles, but they do not directly prescribe record splitting, facts schemas, coverage profiles, cache explanation UX, or sensitive presets. Those are repository-specific product decisions.

## Selection Criteria

Use these gates before adding an item to the roadmap.

| Gate | Question | Keep if |
| --- | --- | --- |
| Exact-cache fit | Does it strengthen reuse of unchanged documents or structured state? | Yes |
| Determinism | Can the behavior be proven locally without live provider calls? | Yes, unless explicitly telemetry-only |
| Lightweight surface | Does it avoid new servers, databases, crawlers, dashboards, or broad frameworks? | Yes |
| Existing-design fit | Does it reuse `DocumentInput`, `DocumentSummaryState`, `PipelineStats`, or current templates? | Yes |
| User trust | Does it show why something was reused, summarized, missing, or unsafe? | Yes |
| Blast radius | Does it avoid schema churn unless fixture failures prove need? | Yes |

Items that fail two or more gates should be deferred or rejected.

## Recommended Roadmap

### P0: Demo-First Lifecycle

Decision: include.

Problem:

The current repository can prove cache reuse through tests and benchmark output, but a new reader still has to infer the practical workflow. A concise incident lifecycle demo makes the repo's value obvious without changing runtime architecture.

Design:

Add one focused workflow under `examples/incident_lifecycle/`:

```text
examples/incident_lifecycle/
|-- initial.json
|-- update.json
|-- with_update.json
|-- expected_first_brief.md
|-- expected_rerender_action_items.md
|-- expected_after_update.md
`-- README.md
```

The demo should show exactly three runs:

1. First run: ticket plus incident report.
2. Same document set, different render mode.
3. Same initial set plus one update.

Expected stats:

```text
first run:
  summarizer_calls: N
  document_cache_hits: 0
  document_cache_misses: N

mode rerender:
  summarizer_calls: 0
  document_cache_hits: N
  document_cache_misses: 0

add one update:
  summarizer_calls: 1
  document_cache_hits: N
  document_cache_misses: 1
```

Acceptance evidence:

- A docs or fixture test runs the demo commands or validates the expected stats.
- README links to this demo near the top.
- The demo stays small: one workflow, not a library of many domains.

Non-goals:

- Do not add many demo packs at once.
- Do not make the demo require OpenAI credentials.
- Do not turn examples into a tutorial framework.

### P1: Cache Explain / Document Cache Trace

Decision: include.

Problem:

Users need to know why a document was reused or summarized again. Current stats expose counts and cache keys, but not per-document reasons.

Design:

Add a small event model to stats, for example:

```python
class DocumentCacheEvent(BaseModel):
    document_id: str
    fingerprint_prefix: str
    cache_key_prefix: str
    status: Literal["hit", "miss", "expired", "corrupt", "bypass", "refresh", "ephemeral"]
    reason: str
```

Add `document_cache_events: list[DocumentCacheEvent]` to `PipelineStats`.

Reason examples:

```text
same fingerprint, schema, summarizer, redaction policy
new fingerprint
expired cache entry
corrupt cache entry
cache policy bypass
cache policy refresh
ephemeral policy disables reads and writes
```

Statuses such as `bypass`, `refresh`, and `ephemeral` are emitted from policy decisions before cache lookup, not from cache-file reads.

CLI surface:

```bash
python -m document_briefing_cache.cli run \
  --input examples/incident_lifecycle/with_update.json \
  --mode executive \
  --show-stats \
  --explain-cache
```

Possible text output:

```markdown
## Cache explanation

| Document | Fingerprint | Result | Reason |
| --- | --- | --- | --- |
| TCK-4821 | 91ab32f4c012 | hit | same fingerprint, schema, summarizer, redaction policy |
| INC-2026-0703-PAY | aa82c19eaa31 | hit | same fingerprint, schema, summarizer, redaction policy |
| update-2026-07-03-1530 | 93cb710ff991 | miss | new fingerprint |

Output cache:
- result: miss
- reason: render mode changed or output key not present
```

Acceptance evidence:

- Unit tests cover `hit`, `miss`, `expired`, `corrupt`, and policy bypass cases.
- CLI test verifies `--explain-cache` includes document id, fingerprint prefix, status, and reason.
- Output cache explanation is marked best-effort unless the previous output key is available for comparison.

Non-goals:

- Do not build a cache viewer UI.
- Do not expose full cache keys by default; prefixes are enough.
- Do not make explanation require loading all cache files.

### P2: Record Granularity, Narrowly Scoped

Decision: include as an incident-only first slice, then expand only with fixture proof.

Problem:

Large append-only operational files can still invalidate a whole document. The repository already supports JSON list normalization and section-level splitting, but plain text incident update feeds may need more stable record boundaries than heading order alone.

Current baseline:

- JSON arrays under `documents`, `items`, `results`, `records`, `articles`, or `data` already normalize into multiple documents.
- `--split-input-sections` already splits multi-section Markdown-like input into section-level documents.

Design rule:

Do not introduce a broad domain parser. Add a deterministic splitter only for stable operational boundaries.

Candidate CLI:

```bash
python -m document_briefing_cache.cli run \
  --input incident_updates.md \
  --split-records incident \
  --mode brief
```

Initial modes:

```text
none
incident
```

Defer `ticket`, `markdown`, and `auto` modes until false positives are well understood. Existing `--split-input-sections` should remain the Markdown-oriented option until a new mode proves necessary.

First-slice boundary examples:

```text
Incident ID:
Incident Update:
```

Stable ID rule:

Prefer explicit IDs from the record. Fall back to a short fingerprint of the record body. Avoid pure ordinal IDs for append-heavy files because inserting a record can shift later IDs.

Example:

```text
INC-1/root
INC-1/update-20260703-1530
INC-1/update-fp-a13b72
```

Acceptance evidence:

- Tests prove appending a new record preserves old record IDs.
- Benchmark proves old records hit and only the new record misses.
- Tests cover `Incident ID` and `Incident Update` boundaries.
- Docs explicitly prefer structured JSON input when available.

Non-goals:

- Do not infer complex ticket state machines.
- Do not add ticket or Markdown-specific parsing in the first slice.
- Do not fetch remote tickets.
- Do not parse every tracker format.
- Do not make record splitting the default for all text.

### P3: Workflow Evals And Nuance Fixtures

Decision: include.

Problem:

Some high-value claims are not covered by simple cache stats. The repository needs fixtures that prove the skill preserves nuance and exposes gaps.

Add eval cases for:

1. Add-one-record cache reuse.
2. Mode-only rerender without summarizer calls.
3. "Mitigated" must not become "Resolved".
4. "No duplicate charges have been observed" must not become "there were no duplicate charges".
5. Communication restrictions must be preserved as constraints or unknowns.
6. Missing incident fields should surface warnings or unknowns if a profile/checklist is applied later.

Acceptance evidence:

- `scripts/validate_skill.py --run-evals` validates the new fixtures.
- Fixtures assert both output text and `DocumentSummaryState` fields where possible.
- For LLM-backed behavior, fixtures separate deterministic schema expectations from live model quality expectations.

Non-goals:

- Do not claim live model invocation rate unless actual host telemetry was captured.
- Do not make static trigger evals stand in for real implicit-routing telemetry.

### P4: Skill Metadata Tightening

Decision: include.

Problem:

The current metadata is directionally correct, but the short description can be sharper. Skill routing benefits from clear trigger-oriented descriptions.

Recommended short description:

```text
Reuse cached structured summaries for supplied documents; rerender briefs, digests, actions, risks, and metrics without re-summarizing unchanged content.
```

Good triggers:

```text
summarize these supplied documents and cache the structured state
rerender the same document as action_items without reprocessing
brief these tickets/reports/logs and show cache stats
add this new update and reuse previous document summaries
```

Bad triggers:

```text
summarize anything
research topic
analyze code
write article
```

Acceptance evidence:

- Static trigger evals cover positive and near-miss boundary cases.
- `agents/openai.yaml` remains concise and does not duplicate long `SKILL.md` content.
- `SKILL.md` remains the procedural source of truth.

### P5: Sensitive Preset

Decision: include as a thin alias only.

Problem:

Safe settings exist, but users must remember several flags.

Design:

Add:

```bash
--sensitive
```

It expands to:

```text
--cache-policy ephemeral
--no-output-cache
--redact-pii
--delete-on-exit created
```

Output should make the preset visible by reusing existing stats and display fields where possible:

```text
cache_policy: ephemeral
output_cache: disabled
pii_redactions: 8
delete_on_exit_applied: true
sensitive_mode: true  # display-only alias marker
```

Acceptance evidence:

- CLI test verifies the option expansion.
- Cache lifecycle tests verify no document summaries or rendered outputs persist after the run.
- Docs clearly state redaction is best-effort and not complete DLP.

Deferred extension:

`--redact-secrets` may be added later as an optional best-effort regex profile for bearer tokens, API keys, webhook secrets, session ids, and card-like values. Do not bundle it into `--sensitive` until its false-positive behavior is tested.

## Deferred Items

### Facts Schema

Decision: defer.

Potential value:

`facts` with `kind`, `subject`, `value`, `polarity`, and evidence could preserve important non-action/non-risk information such as status, impact, workaround, communication restrictions, and "not observed" statements.

Reason to defer:

This touches schema versioning, strict LLM output, evidence validation, merge behavior, render templates, tests, docs, and migration expectations. The current schema already has evidence-backed summary, key points, decisions, actions, risks, metrics, unknowns, open questions, and section digests.

Entry condition:

Add failing eval fixtures first:

```text
Mitigated must not become Resolved.
No duplicate charges observed must not become no duplicate charges.
Do not disclose root cause before Legal approval must remain a constraint.
```

If existing fields cannot represent those safely, add the smallest possible schema extension.

### Coverage Profiles

Decision: defer.

Potential value:

Profiles can warn when expected fields such as incident id, status, impact, owner, or root cause are missing.

Reason to defer:

The benchmark already has structural quality coverage. A profile DSL can grow into domain configuration sprawl.

Entry condition:

Start with eval-only checklists. Promote to runtime `--profile` only after repeated fixtures show value.

### Provider Usage Metrics

Decision: defer.

Potential value:

OpenAI usage data can distinguish provider prompt cache from local document cache and record `input_tokens`, `output_tokens`, `cached_tokens`, model, and latency.

Reason to defer:

It is provider-specific and only proves value with live telemetry. The core product claim is stronger: rerenders and unchanged documents avoid provider calls entirely.

Entry condition:

Implement only after there is a real OpenAI-backed benchmark run to store or compare against.

## Rejected Items

### Semantic Cache As A Default

Reject.

Reason:

Small differences in dates, counts, policy text, legal status, or incident impact can matter. Exact fingerprinting should remain the default for document briefing.

### Vector DB / RAG

Reject.

Reason:

The repository is about repeated briefing reuse, not retrieval. Adding RAG changes the product category and expands the maintenance and correctness surface.

### Built-In URL Fetching

Reject.

Reason:

URL fetching introduces freshness, authentication, robots, SSRF, network, rate-limit, and prompt-injection concerns. Keep the boundary: callers provide local files or normalized payloads.

### Dashboard / Server UI

Reject.

Reason:

A small HTML report may be acceptable later, but a dashboard/server would dilute the skill's lightweight packaging.

### Complete Privacy Claims

Reject.

Reason:

HMAC is tamper detection, not encryption. Local cache files can contain plaintext summaries and evidence quotes. Documentation should continue to say this plainly.

## Documentation Shape

Keep `SKILL.md` short. Put long explanations here or in nearby reference files.

Recommended reference layout:

```text
references/
|-- architecture.md
|-- best-practices.md
|-- competitive-roadmap.md
|-- llm-contract.md
`-- schema.md
```

Only add more reference files when the topic becomes too large for this document.

Avoid adding:

```text
docs/cache-granularity.md
docs/provider-cache-vs-document-cache.md
docs/privacy.md
```

unless each file has enough unique operational detail to justify the extra navigation.

## Roadmap Summary

| Priority | Item | Status | Why |
| --- | --- | --- | --- |
| P0 | Demo-first lifecycle | Include | Highest clarity, low risk |
| P1 | Cache explain / document cache trace | Include | High trust, high debuggability |
| P2 | Narrow record splitting | Include carefully | Improves hit rate for append-only docs |
| P3 | Workflow and nuance evals | Include | Makes quality claims testable |
| P4 | Skill metadata tightening | Include | Small routing improvement |
| P5 | Sensitive preset | Include as alias | Reduces operational mistakes |
| D1 | Facts schema | Defer | Valuable but high blast radius |
| D2 | Coverage profiles | Defer | Useful after eval proof |
| D3 | Provider usage metrics | Defer | Requires live telemetry to matter |
| R1 | Semantic cache default | Reject | False-hit risk |
| R2 | Vector DB / RAG | Reject | Wrong product category |
| R3 | URL fetcher | Reject | Security and freshness burden |
| R4 | Dashboard/server UI | Reject | Too heavy for a skill |

## Stop Rules

Stop or re-scope if a proposed roadmap item requires:

- a background service,
- a database,
- network fetching,
- broad domain inference,
- long `SKILL.md` additions,
- provider credentials for normal validation,
- claims of complete privacy or security,
- semantic matching for data-sensitive facts.

The repo should remain a compact, exact-cache briefing skill whose claims can be verified with local tests and small examples.

