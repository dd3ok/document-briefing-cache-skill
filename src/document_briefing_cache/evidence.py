from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import DocumentSection, DocumentSummaryState, EvidenceRef


@dataclass(frozen=True)
class ProtectedValue:
    kind: str
    value: str
    normalized: str
    path: str | None = None
    span: tuple[int, int] | None = None


PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("id", re.compile(r"\b[A-Z][A-Z0-9]+-\d{2,}(?:-\d+)*\b")),
    ("percent", re.compile(r"-?\d+(?:\.\d+)?\s*%")),
    ("currency", re.compile(r"(?:USD|KRW|\$|₩)\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:USD|KRW|원)")),
    ("duration", re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|sec|s|초|days?|일)\b", re.IGNORECASE)),
    ("name", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")),
    ("number", re.compile(r"(?<![\w.-])-?\d[\d,]*(?:\.\d+)?(?![\w.-])")),
)


def normalize_protected_value(value: str) -> str:
    return re.sub(r"[\s,]+", "", value).lower()


def extract_protected_values(text: str | None, raw: Any | None = None) -> list[ProtectedValue]:
    values: dict[tuple[str, str, str | None], ProtectedValue] = {}
    for value in _extract_from_text(text or ""):
        values[(value.kind, value.normalized, value.path)] = value
    for path, leaf in _walk_raw(raw):
        for value in _extract_from_text(str(leaf), path=path):
            values[(value.kind, value.normalized, value.path)] = value
    return list(values.values())


def validate_summary_evidence(
    summary: DocumentSummaryState,
    source_text: str,
    sections: list[DocumentSection] | None = None,
    raw: Any | None = None,
) -> list[str]:
    errors: list[str] = []
    source_values = {value.normalized: value.value for value in extract_protected_values(source_text, raw=raw)}
    section_map = {section.section_id: section.text for section in sections or []}

    for idx, point in enumerate(summary.key_points):
        if point.text and not _has_source_evidence(point.evidence):
            errors.append(f"key point evidence is required: {idx}")
    for idx, decision in enumerate(summary.decisions):
        if decision.text and not _has_source_evidence(decision.evidence):
            errors.append(f"decision evidence is required: {idx}")
    for idx, action in enumerate(summary.actions):
        if action.action and not _has_source_evidence(action.evidence):
            errors.append(f"action evidence is required: {idx}")
    for idx, risk in enumerate(summary.risks):
        if risk.title and not _has_source_evidence(risk.evidence):
            errors.append(f"risk evidence is required: {idx}")
    for idx, metric in enumerate(summary.metrics):
        if metric.value and not _has_source_evidence(metric.evidence):
            errors.append(f"metric evidence is required: {idx}")

    for evidence in _iter_evidence(summary):
        errors.extend(_validate_evidence_ref(evidence, summary.document_id, source_text, section_map))

    for label, text in _iter_claim_text(summary):
        for value in extract_protected_values(text):
            if value.normalized not in source_values:
                errors.append(f"{label} contains protected value not found in source: {value.value}")

    for metric in summary.metrics:
        metric_value = f"{metric.value}{metric.unit or ''}" if metric.unit == "%" else f"{metric.value} {metric.unit}".strip()
        if metric.unit is None and metric.value in source_text:
            continue
        if normalize_protected_value(metric_value) not in source_values and normalize_protected_value(metric.value) not in source_values:
            errors.append(f"metric contains protected value not found in source: {metric_value}")

    for action in summary.actions:
        if action.due and normalize_protected_value(action.due) not in source_values:
            errors.append(f"action due contains protected value not found in source: {action.due}")

    return errors


def _has_source_evidence(evidence_refs: list[EvidenceRef]) -> bool:
    return any(bool(ref.quote) for ref in evidence_refs)


def _extract_from_text(text: str, path: str | None = None) -> list[ProtectedValue]:
    values: list[ProtectedValue] = []
    occupied: list[range] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            span = range(match.start(), match.end())
            if any(_overlaps(span, existing) for existing in occupied):
                continue
            occupied.append(span)
            raw_value = match.group(0).strip()
            values.append(ProtectedValue(kind=kind, value=raw_value, normalized=normalize_protected_value(raw_value), path=path, span=(match.start(), match.end())))
    return values


def _walk_raw(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_raw(child, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _walk_raw(child, f"{path}[{idx}]")
    elif value is not None:
        yield path, value


def _overlaps(left: range, right: range) -> bool:
    return left.start < right.stop and right.start < left.stop


def _iter_evidence(summary: DocumentSummaryState):
    for point in summary.key_points:
        yield from point.evidence
    for decision in summary.decisions:
        yield from decision.evidence
    for action in summary.actions:
        yield from action.evidence
    for risk in summary.risks:
        yield from risk.evidence
    for metric in summary.metrics:
        yield from metric.evidence


def _iter_claim_text(summary: DocumentSummaryState):
    yield "summary", summary.summary
    for point in summary.key_points:
        yield "key point", point.text
    for decision in summary.decisions:
        yield "decision", decision.text
        yield "decision owner", decision.owner or ""
    for action in summary.actions:
        yield "action", action.action
        yield "action owner", action.owner or ""
    for risk in summary.risks:
        yield "risk", risk.title
        yield "risk reason", risk.reason or ""
    for question in summary.open_questions:
        yield "open question", question
    for digest in summary.sections_digest:
        yield "section digest", digest.summary


def _validate_evidence_ref(
    evidence: EvidenceRef,
    document_id: str,
    source_text: str,
    section_map: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    if evidence.document_id != document_id:
        errors.append(f"evidence document_id mismatch: {evidence.document_id}")
    if not evidence.quote:
        errors.append("evidence quote is required for source-backed claims")
    haystack = source_text
    if evidence.section_id:
        if evidence.section_id not in section_map:
            errors.append(f"evidence section_id not found: {evidence.section_id}")
        else:
            haystack = section_map[evidence.section_id]
    if evidence.quote and _squash_space(evidence.quote) not in _squash_space(haystack):
        errors.append(f"evidence quote not found in source: {evidence.quote}")
    return errors


def _squash_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
