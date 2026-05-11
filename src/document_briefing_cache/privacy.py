from __future__ import annotations

import re
from typing import Any

from .models import DocumentInput, DocumentSummaryState


NO_REDACTION_POLICY_ID = "none"
REDACTION_POLICY_ID = "basic-contact-v1"


PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED:email]"),
    ("phone", re.compile(r"\b01[016789][-\s]?\d{3,4}[-\s]?\d{4}\b"), "[REDACTED:phone]"),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[REDACTED:phone]"),
)


def redact_pii_text(value: str) -> tuple[str, int]:
    redacted = value
    total = 0
    for _kind, pattern, replacement in PII_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        total += count
    return redacted, total


def redact_pii_data(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return redact_pii_text(value)
    if isinstance(value, list):
        redacted_items = []
        total = 0
        for item in value:
            redacted_item, count = redact_pii_data(item)
            redacted_items.append(redacted_item)
            total += count
        return redacted_items, total
    if isinstance(value, dict):
        redacted_dict = {}
        total = 0
        for key, item in value.items():
            redacted_item, count = redact_pii_data(item)
            redacted_dict[key] = redacted_item
            total += count
        return redacted_dict, total
    return value, 0


def redaction_policy_id(redact_pii: bool) -> str:
    return REDACTION_POLICY_ID if redact_pii else NO_REDACTION_POLICY_ID


def redact_document_input(document: DocumentInput) -> tuple[DocumentInput, int]:
    payload = document.model_dump(mode="json")
    redacted_payload, count = redact_pii_data(payload)
    if not isinstance(redacted_payload, dict):
        return document, 0

    for identity_field in ("document_id", "source"):
        original_value = payload.get(identity_field)
        redacted_value = redacted_payload.get(identity_field)
        if isinstance(original_value, str) and original_value != redacted_value:
            redacted_payload[identity_field] = None

    return DocumentInput.model_validate(redacted_payload), count


def redact_summary_state(summary: DocumentSummaryState) -> tuple[DocumentSummaryState, int]:
    payload = summary.model_dump(mode="json")
    redacted_payload, count = redact_pii_data(payload)
    if isinstance(redacted_payload, dict):
        if payload.get("document_id") != redacted_payload.get("document_id"):
            redacted_payload["document_id"] = summary.content_fingerprint[:16]
        if payload.get("source") != redacted_payload.get("source"):
            redacted_payload["source"] = None
    return DocumentSummaryState.model_validate(redacted_payload), count
