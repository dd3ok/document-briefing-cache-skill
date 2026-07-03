from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .models import ContentFormat, DocumentInput, DocumentSection, DocumentType

TEXT_KEYS = ("text", "body", "content", "description", "summary", "notes", "message", "transcript")
TITLE_KEYS = ("title", "name", "subject", "headline")
SOURCE_KEYS = ("source", "url", "link", "path")
ID_KEYS = ("id", "document_id", "doc_id", "uuid", "url")
NORMALIZATION_UNKNOWNS_KEY = "normalization_unknowns"


def normalization_unknown(message: str) -> dict[str, list[str]]:
    return {NORMALIZATION_UNKNOWNS_KEY: [message]}


def read_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def detect_format_from_path(path: str | Path) -> ContentFormat:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return ContentFormat.json
    if suffix in {".xml", ".rss", ".atom"}:
        return ContentFormat.xml
    if suffix in {".html", ".htm"}:
        return ContentFormat.html
    if suffix in {".md", ".markdown"}:
        return ContentFormat.markdown
    if suffix == ".pdf":
        return ContentFormat.pdf_text
    return ContentFormat.text


def load_path_to_documents(path: str | Path) -> list[DocumentInput]:
    path = Path(path)
    fmt = detect_format_from_path(path)
    if fmt == ContentFormat.pdf_text:
        return [load_pdf_as_document(path)]
    raw = read_file(path)
    return normalize_payload(raw, source=str(path), content_format=fmt)


def load_pdf_as_document(path: str | Path) -> DocumentInput:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError("Install with `pip install -e .[pdf]` to load PDF files.") from exc

    reader = PdfReader(str(path))
    pages = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[page {idx + 1}]\n{page_text}")
    return DocumentInput(
        title=Path(path).stem,
        source=str(path),
        doc_type=DocumentType.unknown,
        content_format=ContentFormat.pdf_text,
        text="\n\n".join(pages),
        metadata={"pages": len(reader.pages)},
    )


def normalize_payload(
    payload: Any,
    source: str | None = None,
    content_format: ContentFormat | str = ContentFormat.unknown,
) -> list[DocumentInput]:
    if isinstance(content_format, str):
        try:
            content_format = ContentFormat(content_format)
        except ValueError:
            content_format = ContentFormat.unknown

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    if isinstance(payload, str):
        text = payload.strip()
        fmt = content_format
        if fmt == ContentFormat.unknown:
            fmt = guess_format_from_string(text)

        if fmt == ContentFormat.json:
            return normalize_json_string(text, source)
        if fmt == ContentFormat.xml:
            return [normalize_xml_string(text, source)]
        if fmt == ContentFormat.html:
            return [normalize_html_string(text, source)]
        return [DocumentInput(source=source, content_format=fmt, text=text, doc_type=infer_doc_type(text))]

    if isinstance(payload, (dict, list)):
        return normalize_json_object(payload, source=source)

    return [
        DocumentInput(
            source=source,
            content_format=ContentFormat.text,
            text=str(payload),
            doc_type=DocumentType.unknown,
            metadata=normalization_unknown(f"Unsupported payload type: {type(payload).__name__}"),
        )
    ]


def guess_format_from_string(text: str) -> ContentFormat:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return ContentFormat.json
    if stripped.startswith("<") and re.search(r"<\w+[^>]*>", stripped[:200]):
        if "<html" in stripped[:500].lower() or "<!doctype html" in stripped[:500].lower():
            return ContentFormat.html
        return ContentFormat.xml
    if re.search(r"^#{1,6}\s+", stripped, flags=re.MULTILINE):
        return ContentFormat.markdown
    return ContentFormat.text


def normalize_json_string(text: str, source: str | None = None) -> list[DocumentInput]:
    return normalize_json_object(json.loads(text), source=source)


def normalize_json_object(value: Any, source: str | None = None) -> list[DocumentInput]:
    if isinstance(value, list):
        return [document_from_mapping(item, source=source, fallback_index=i) if isinstance(item, dict)
                else DocumentInput(source=source, raw=item, text=flatten_json(item), content_format=ContentFormat.json, doc_type=DocumentType.api_payload)
                for i, item in enumerate(value)]

    if isinstance(value, dict):
        for list_key in ("documents", "items", "results", "records", "articles", "data"):
            if isinstance(value.get(list_key), list):
                docs = []
                for i, item in enumerate(value[list_key]):
                    if isinstance(item, dict):
                        docs.append(document_from_mapping(item, source=source, fallback_index=i))
                    else:
                        docs.append(DocumentInput(source=source, raw=item, text=flatten_json(item), content_format=ContentFormat.json, doc_type=DocumentType.api_payload))
                return docs
        return [document_from_mapping(value, source=source)]

    return [DocumentInput(source=source, raw=value, text=flatten_json(value), content_format=ContentFormat.json, doc_type=DocumentType.api_payload)]


def document_from_mapping(item: dict[str, Any], source: str | None = None, fallback_index: int | None = None) -> DocumentInput:
    title = first_value(item, TITLE_KEYS)
    doc_source = first_value(item, SOURCE_KEYS) or source
    document_id = first_value(item, ID_KEYS)
    body = first_value(item, TEXT_KEYS)
    text = str(body) if body is not None else flatten_json(item)
    doc_type = infer_doc_type(text, title=title, metadata=item)
    if doc_type == DocumentType.unknown:
        doc_type = DocumentType.api_payload
    if document_id is None and doc_source is None and fallback_index is not None:
        document_id = f"item-{fallback_index}"
    return DocumentInput(
        document_id=str(document_id) if document_id is not None else None,
        title=str(title) if title is not None else None,
        source=str(doc_source) if doc_source is not None else None,
        doc_type=doc_type,
        content_format=ContentFormat.json,
        text=text,
        raw=item,
        metadata={k: v for k, v in item.items() if k not in set(TEXT_KEYS)},
    )


def first_value(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any | None:
    lowered = {str(k).lower(): k for k in mapping.keys()}
    for key in keys:
        if key in lowered:
            value = mapping[lowered[key]]
            if value not in (None, ""):
                return value
    return None


def flatten_json(value: Any, prefix: str = "") -> str:
    lines: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value.keys(), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            lines.append(flatten_json(value[key], path))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            path = f"{prefix}[{idx}]"
            lines.append(flatten_json(item, path))
    else:
        lines.append(f"{prefix}: {value}")
    return "\n".join(line for line in lines if line)


def normalize_html_string(text: str, source: str | None = None) -> DocumentInput:
    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    plain = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n")).strip()
    return DocumentInput(title=title, source=source, content_format=ContentFormat.html, text=plain, doc_type=DocumentType.web_page)


def normalize_xml_string(text: str, source: str | None = None) -> DocumentInput:
    try:
        root = ET.fromstring(text)
        title = root.attrib.get("title") or root.findtext("title")
        plain = flatten_xml(root)
    except ET.ParseError:
        title = None
        plain = text
    return DocumentInput(title=title, source=source, content_format=ContentFormat.xml, text=plain, doc_type=DocumentType.api_payload)


def flatten_xml(node: ET.Element, prefix: str = "") -> str:
    tag = node.tag.split("}")[-1]
    path = f"{prefix}.{tag}" if prefix else tag
    parts: list[str] = []
    text = (node.text or "").strip()
    if text:
        parts.append(f"{path}: {text}")
    for key, value in sorted(node.attrib.items()):
        parts.append(f"{path}@{key}: {value}")
    for child in list(node):
        parts.append(flatten_xml(child, path))
    return "\n".join(part for part in parts if part)


def infer_doc_type(text: str | None, title: str | None = None, metadata: dict[str, Any] | None = None) -> DocumentType:
    haystack = " ".join([text or "", title or "", " ".join(map(str, (metadata or {}).keys()))]).lower()
    if any(token in haystack for token in ("meeting", "회의", "minutes", "attendees", "참석")):
        return DocumentType.meeting_notes
    if any(token in haystack for token in ("incident", "error", "장애", "오류", "outage", "log")):
        return DocumentType.log
    if any(token in haystack for token in ("policy", "규정", "약관", "manual", "가이드")):
        return DocumentType.policy
    if any(token in haystack for token in ("ticket", "jira", "issue", "github", "bug")):
        return DocumentType.ticket
    if any(token in haystack for token in ("from:", "to:", "subject:", "email", "메일")):
        return DocumentType.email
    if any(token in haystack for token in ("report", "보고서", "quarter", "분기")):
        return DocumentType.report
    if any(token in haystack for token in ("transcript", "대화록", "녹취")):
        return DocumentType.transcript
    if any(token in haystack for token in ("article", "news", "기사", "breaking")):
        return DocumentType.news
    return DocumentType.unknown


def split_into_sections(text: str, max_chars: int = 2500) -> list[DocumentSection]:
    text = (text or "").strip()
    if not text:
        return []

    heading_pattern = re.compile(r"^(#{1,6}\s+.+|[A-Z가-힣][^\n]{0,80}:)\s*$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))
    sections: list[DocumentSection] = []

    if matches:
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading = match.group(1).strip().lstrip("#").strip().rstrip(":")
            body = text[start:end].strip()
            if body:
                sections.extend(chunk_text(body, heading=heading, start_order=len(sections), max_chars=max_chars))
    else:
        sections = chunk_text(text, heading=None, start_order=0, max_chars=max_chars)

    return sections


def split_documents_into_section_documents(documents: list[DocumentInput]) -> list[DocumentInput]:
    split_documents: list[DocumentInput] = []
    for index, document in enumerate(documents):
        sections = split_into_sections(document.text or "")
        if len(sections) <= 1:
            split_documents.append(document)
            continue

        parent_id = document.document_id or document.source or f"document-{index}"
        for section in sections:
            section_id = f"section-{section.order + 1}"
            split_documents.append(
                DocumentInput(
                    document_id=f"{parent_id}#{section_id}",
                    title=section.heading or document.title,
                    source=document.source,
                    doc_type=document.doc_type,
                    content_format=document.content_format,
                    text=section.text,
                    raw=document.raw,
                    metadata={
                        **document.metadata,
                        "parent_document_id": parent_id,
                        "parent_title": document.title,
                        "section_id": section_id,
                        "section_heading": section.heading,
                    },
                )
            )
    return split_documents


def chunk_text(text: str, heading: str | None, start_order: int, max_chars: int) -> list[DocumentSection]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            if len(paragraph) > max_chars:
                for i in range(0, len(paragraph), max_chars):
                    chunks.append(paragraph[i:i + max_chars])
                current = ""
            else:
                current = paragraph
    if current:
        chunks.append(current)

    return [
        DocumentSection(
            section_id=f"s{start_order + i + 1}",
            order=start_order + i,
            heading=heading,
            text=chunk,
            char_count=len(chunk),
        )
        for i, chunk in enumerate(chunks)
    ]
