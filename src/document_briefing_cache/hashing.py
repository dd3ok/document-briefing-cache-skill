from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .models import DocumentInput, DocumentSummaryState


def normalize_text_for_hash(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def document_content_fingerprint(document: DocumentInput) -> str:
    payload = {
        "title": document.title or "",
        "source": document.source or "",
        "doc_type": str(document.doc_type),
        "content_format": str(document.content_format),
        "text": normalize_text_for_hash(document.text),
        "raw": document.raw if document.text is None else None,
    }
    return sha256_text(stable_json(payload))


def stable_document_id(document: DocumentInput, fingerprint: str) -> str:
    if document.document_id:
        return document.document_id
    if document.source:
        return sha256_text(document.source)[:16]
    return fingerprint[:16]


def document_summary_cache_key(
    document: DocumentInput,
    fingerprint: str,
    summarizer_id: str,
    skill_version: str,
    schema_version: str = "1.0.0",
    redaction_policy_id: str = "none",
) -> str:
    payload = {
        "type": "document_summary",
        "schema_version": schema_version,
        "skill_version": skill_version,
        "summarizer_id": summarizer_id,
        "redaction_policy_id": redaction_policy_id,
        "fingerprint": fingerprint,
        "document_id": stable_document_id(document, fingerprint),
    }
    return sha256_text(stable_json(payload))


def output_cache_key(
    summaries_or_documents: list[DocumentSummaryState] | list[DocumentInput],
    mode: str,
    audience: str,
    locale: str,
    skill_version: str,
    template_version: str,
    summarizer_id: str,
    redaction_policy_id: str = "none",
) -> str:
    item_payload = []
    for item in summaries_or_documents:
        if isinstance(item, DocumentSummaryState):
            item_payload.append({
                "document_id": item.document_id,
                "fingerprint": item.content_fingerprint,
                "summarizer_id": item.summarizer_id,
                "schema_version": item.schema_version,
            })
        else:
            fingerprint = document_content_fingerprint(item)
            item_payload.append({
                "document_id": stable_document_id(item, fingerprint),
                "fingerprint": fingerprint,
                "summarizer_id": summarizer_id,
                "schema_version": "1.0.0",
            })

    payload = {
        "type": "rendered_output",
        "mode": mode,
        "audience": audience,
        "locale": locale,
        "skill_version": skill_version,
        "template_version": template_version,
        "summarizer_id": summarizer_id,
        "redaction_policy_id": redaction_policy_id,
        "items": item_payload,
    }
    return sha256_text(stable_json(payload))
