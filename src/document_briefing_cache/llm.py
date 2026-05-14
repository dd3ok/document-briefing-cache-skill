from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TypeVar

from .models import (
    ActionItem,
    Decision,
    DocumentSection,
    DocumentSummaryState,
    EvidenceRef,
    KeyPoint,
    Metric,
    Risk,
    SectionDigest,
)


@dataclass(frozen=True)
class LLMConfig:
    timeout_seconds: float = 60.0
    max_retries: int = 2
    retry_initial_delay_seconds: float = 1.0
    max_input_tokens: int = 12000
    max_output_tokens: int = 4000


def estimate_tokens(text: str | None) -> int:
    return max(1, (len(text or "") + 3) // 4)


def chunk_sections_by_budget(sections: list[DocumentSection], config: LLMConfig) -> list[list[DocumentSection]]:
    chunks: list[list[DocumentSection]] = []
    current: list[DocumentSection] = []
    current_tokens = 0
    max_input_tokens = max(1, config.max_input_tokens)

    for section in sections:
        section_tokens = estimate_tokens(section.text)
        if current and current_tokens + section_tokens > max_input_tokens:
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append(section)
        current_tokens += section_tokens

        if section_tokens > max_input_tokens:
            chunks.append(current)
            current = []
            current_tokens = 0

    if current:
        chunks.append(current)
    return chunks


def merge_document_states(partials: list[DocumentSummaryState]) -> DocumentSummaryState:
    if not partials:
        raise ValueError("Cannot merge an empty list of document summary states.")

    first = partials[0]
    for state in partials[1:]:
        if state.document_id != first.document_id:
            raise ValueError("Cannot merge document summary states with different document_id values.")
        if state.content_fingerprint != first.content_fingerprint:
            raise ValueError("Cannot merge document summary states with different content_fingerprint values.")

    merged = first.model_copy(deep=True)
    merged.summary = "\n\n".join(_dedupe_strings(state.summary for state in partials if state.summary))
    merged.summary_evidence = _dedupe_models(_flatten(state.summary_evidence for state in partials), _evidence_key)
    merged.key_points = _dedupe_models(_flatten(state.key_points for state in partials), _key_point_key)
    merged.decisions = _dedupe_models(_flatten(state.decisions for state in partials), _decision_key)
    merged.actions = _dedupe_models(_flatten(state.actions for state in partials), _action_key)
    merged.risks = _dedupe_models(_flatten(state.risks for state in partials), _risk_key)
    merged.metrics = _dedupe_models(_flatten(state.metrics for state in partials), _metric_key)
    merged.entities = _dedupe_strings(_flatten(state.entities for state in partials))
    merged.topics = _dedupe_strings(_flatten(state.topics for state in partials))
    merged.open_questions = _dedupe_strings(_flatten(state.open_questions for state in partials))
    merged.unknowns = _dedupe_strings(_flatten(state.unknowns for state in partials))
    merged.sections_digest = _dedupe_models(_flatten(state.sections_digest for state in partials), _section_digest_key)
    merged.importance = max(state.importance for state in partials)
    return merged


T = TypeVar("T")


def _flatten(items: Iterable[Iterable[T]]) -> list[T]:
    return [item for group in items for item in group]


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_models(values: Iterable[T], key_func) -> list[T]:
    seen: set[tuple] = set()
    result: list[T] = []
    for value in values:
        key = key_func(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _evidence_quotes(evidence_refs: list[EvidenceRef]) -> tuple[str | None, ...]:
    return tuple(evidence.quote for evidence in evidence_refs)


def _evidence_key(evidence_ref: EvidenceRef) -> tuple:
    return (
        evidence_ref.document_id,
        evidence_ref.section_id,
        evidence_ref.source,
        evidence_ref.path,
        evidence_ref.quote,
    )


def _key_point_key(key_point: KeyPoint) -> tuple:
    return key_point.text, _evidence_quotes(key_point.evidence)


def _decision_key(decision: Decision) -> tuple:
    return decision.text, decision.owner, _evidence_quotes(decision.evidence)


def _action_key(action: ActionItem) -> tuple:
    return action.action, action.owner, action.due, action.status, _evidence_quotes(action.evidence)


def _risk_key(risk: Risk) -> tuple:
    return risk.title, risk.reason, risk.severity, _evidence_quotes(risk.evidence)


def _metric_key(metric: Metric) -> tuple:
    return metric.name, metric.value, metric.unit, _evidence_quotes(metric.evidence)


def _section_digest_key(section_digest: SectionDigest) -> tuple:
    return section_digest.section_id, section_digest.summary, _evidence_quotes(section_digest.evidence)
