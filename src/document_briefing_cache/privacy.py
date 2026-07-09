from __future__ import annotations

import re
from typing import Any

from .models import DocumentInput, DocumentSummaryState


NO_REDACTION_POLICY_ID = "none"
REDACTION_POLICY_ID = "basic-contact-v2"
SECRET_REDACTION_POLICY_ID = "basic-secrets-v1"


PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED:email]"),
    ("kr-registration-id", re.compile(r"(?<!\d)\d{6}-[1-8]\d{6}(?!\d)"), "[REDACTED:kr-registration-id]"),
    ("phone", re.compile(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b"), "[REDACTED:phone]"),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[REDACTED:phone]"),
)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?P<key_quote>[\"']?)"
    r"\b(?P<name>api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|client[_-]?secret|webhook[_-]?secret|session[_-]?id|secret)\b"
    r"(?P=key_quote)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9._~+/=_-]{7,})"
    r"(?P=quote)",
    flags=re.IGNORECASE,
)
SECRET_FIELD_PATTERN = re.compile(
    r"^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|client[_-]?secret|webhook[_-]?secret|session[_-]?id|secret)$",
    flags=re.IGNORECASE,
)
BEARER_TOKEN_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", flags=re.IGNORECASE)
WEBHOOK_URL_PATTERN = re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{12,}", flags=re.IGNORECASE)
CARD_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def redact_pii_text(value: str) -> tuple[str, int]:
    redacted = value
    total = 0
    for _kind, pattern, replacement in PII_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        total += count
    return redacted, total


def redact_secret_text(value: str) -> tuple[str, int]:
    redacted = value
    total = 0

    def replace_assignment(match: re.Match[str]) -> str:
        key_quote = match.group("key_quote")
        value_quote = match.group("quote")
        return f"{key_quote}{match.group('name')}{key_quote}{match.group('sep')}{value_quote}[REDACTED:secret]{value_quote}"

    redacted, count = SECRET_ASSIGNMENT_PATTERN.subn(replace_assignment, redacted)
    total += count
    redacted, count = BEARER_TOKEN_PATTERN.subn("Bearer [REDACTED:secret]", redacted)
    total += count
    redacted, count = WEBHOOK_URL_PATTERN.subn("[REDACTED:webhook-url]", redacted)
    total += count
    redacted, count = redact_luhn_cards(redacted)
    total += count
    return redacted, total


def redact_luhn_cards(value: str) -> tuple[str, int]:
    total = 0

    def replace_card(match: re.Match[str]) -> str:
        nonlocal total
        candidate = match.group(0)
        digits = re.sub(r"\D", "", candidate)
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            total += 1
            return "[REDACTED:card]"
        return candidate

    return CARD_CANDIDATE_PATTERN.sub(replace_card, value), total


def luhn_valid(digits: str) -> bool:
    checksum = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
    return checksum % 10 == 0


def redact_configured_text(value: str, *, redact_pii: bool, redact_secrets: bool) -> tuple[str, int, int]:
    redacted = value
    pii_count = 0
    secret_count = 0
    if redact_pii:
        redacted, pii_count = redact_pii_text(redacted)
    if redact_secrets:
        redacted, secret_count = redact_secret_text(redacted)
    return redacted, pii_count, secret_count


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


def redact_configured_data(value: Any, *, redact_pii: bool, redact_secrets: bool) -> tuple[Any, int, int]:
    if isinstance(value, str):
        return redact_configured_text(value, redact_pii=redact_pii, redact_secrets=redact_secrets)
    if isinstance(value, list):
        redacted_items = []
        pii_total = 0
        secret_total = 0
        for item in value:
            redacted_item, pii_count, secret_count = redact_configured_data(
                item,
                redact_pii=redact_pii,
                redact_secrets=redact_secrets,
            )
            redacted_items.append(redacted_item)
            pii_total += pii_count
            secret_total += secret_count
        return redacted_items, pii_total, secret_total
    if isinstance(value, dict):
        redacted_dict = {}
        pii_total = 0
        secret_total = 0
        for key, item in value.items():
            if redact_secrets and isinstance(key, str) and SECRET_FIELD_PATTERN.match(key) and isinstance(item, str) and item:
                redacted_dict[key] = "[REDACTED:secret]"
                secret_total += 1
                continue
            redacted_item, pii_count, secret_count = redact_configured_data(
                item,
                redact_pii=redact_pii,
                redact_secrets=redact_secrets,
            )
            redacted_dict[key] = redacted_item
            pii_total += pii_count
            secret_total += secret_count
        return redacted_dict, pii_total, secret_total
    return value, 0, 0


def redaction_policy_id(redact_pii: bool, redact_secrets: bool = False) -> str:
    policies = []
    if redact_pii:
        policies.append(REDACTION_POLICY_ID)
    if redact_secrets:
        policies.append(SECRET_REDACTION_POLICY_ID)
    return "+".join(policies) if policies else NO_REDACTION_POLICY_ID


def redact_document_input(document: DocumentInput) -> tuple[DocumentInput, int]:
    redacted, pii_count, _secret_count = redact_configured_document_input(document, redact_pii=True, redact_secrets=False)
    return redacted, pii_count


def redact_configured_document_input(
    document: DocumentInput,
    *,
    redact_pii: bool,
    redact_secrets: bool,
) -> tuple[DocumentInput, int, int]:
    payload = document.model_dump(mode="json")
    redacted_payload, pii_count, secret_count = redact_configured_data(
        payload,
        redact_pii=redact_pii,
        redact_secrets=redact_secrets,
    )
    if not isinstance(redacted_payload, dict):
        return document, 0, 0

    for identity_field in ("document_id", "source"):
        original_value = payload.get(identity_field)
        redacted_value = redacted_payload.get(identity_field)
        if isinstance(original_value, str) and original_value != redacted_value:
            redacted_payload[identity_field] = None

    return DocumentInput.model_validate(redacted_payload), pii_count, secret_count


def redact_summary_state(summary: DocumentSummaryState) -> tuple[DocumentSummaryState, int]:
    payload = summary.model_dump(mode="json")
    redacted_payload, count = redact_pii_data(payload)
    if isinstance(redacted_payload, dict):
        if payload.get("document_id") != redacted_payload.get("document_id"):
            redacted_payload["document_id"] = summary.content_fingerprint[:16]
        if payload.get("source") != redacted_payload.get("source"):
            redacted_payload["source"] = None
    return DocumentSummaryState.model_validate(redacted_payload), count
