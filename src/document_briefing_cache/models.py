from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


DOCUMENT_SUMMARY_SCHEMA_VERSION = "1.1.0"


class ContentFormat(str, Enum):
    text = "text"
    markdown = "markdown"
    html = "html"
    json = "json"
    xml = "xml"
    pdf_text = "pdf_text"
    unknown = "unknown"


class DocumentType(str, Enum):
    report = "report"
    meeting_notes = "meeting_notes"
    email = "email"
    ticket = "ticket"
    log = "log"
    policy = "policy"
    api_payload = "api_payload"
    news = "news"
    web_page = "web_page"
    transcript = "transcript"
    review_comments = "review_comments"
    unknown = "unknown"


class DocumentInput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    document_id: str | None = None
    title: str | None = None
    source: str | None = None
    doc_type: DocumentType | str = DocumentType.unknown
    content_format: ContentFormat | str = ContentFormat.unknown
    text: str | None = None
    raw: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CacheConfig(BaseModel):
    cache_dir: str = ".cache"
    policy: Literal["read_write", "read_only", "refresh", "bypass", "ephemeral", "ttl", "persistent"] = "read_write"
    document_cache: bool = True
    output_cache: bool = False
    document_ttl_seconds: int | None = 30 * 24 * 60 * 60
    output_ttl_seconds: int | None = 24 * 60 * 60
    prune_on_start: bool = False
    prune_on_exit: bool = False
    delete_on_exit: Literal["none", "created", "all"] = "none"
    validate_evidence: bool = True
    cache_hmac_secret_env: str | None = None
    redact_pii: bool = False


class DocumentSection(BaseModel):
    section_id: str
    order: int
    text: str
    heading: str | None = None
    char_count: int = 0


class EvidenceRef(BaseModel):
    document_id: str
    section_id: str | None = None
    source: str | None = None
    path: str | None = None
    quote: str | None = None


class KeyPoint(BaseModel):
    text: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class Decision(BaseModel):
    text: str
    owner: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ActionItem(BaseModel):
    action: str
    owner: str | None = None
    due: str | None = None
    status: Literal["open", "done", "blocked", "unknown"] = "open"
    evidence: list[EvidenceRef] = Field(default_factory=list)


class Risk(BaseModel):
    title: str
    reason: str | None = None
    severity: Literal["critical", "high", "medium", "low", "unknown"] = "unknown"
    evidence: list[EvidenceRef] = Field(default_factory=list)


class Metric(BaseModel):
    name: str | None = None
    value: str
    unit: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class SectionDigest(BaseModel):
    section_id: str
    heading: str | None = None
    summary: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class DocumentSummaryState(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    schema_version: str = DOCUMENT_SUMMARY_SCHEMA_VERSION
    document_id: str
    content_fingerprint: str
    title: str | None = None
    source: str | None = None
    doc_type: DocumentType | str = DocumentType.unknown
    content_format: ContentFormat | str = ContentFormat.unknown
    language: str = "unknown"
    summary: str = ""
    summary_evidence: list[EvidenceRef] = Field(default_factory=list)
    key_points: list[KeyPoint] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    sections_digest: list[SectionDigest] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    summarizer_id: str = "unknown"


class DocumentCacheEvent(BaseModel):
    document_id: str
    title: str | None = None
    fingerprint_prefix: str
    cache_key_prefix: str
    status: Literal["hit", "miss", "expired", "corrupt", "bypass", "refresh", "ephemeral"]
    reason: Literal[
        "hit_same_contract",
        "miss_new_fingerprint",
        "miss_refresh_policy",
        "miss_bypass_policy",
        "miss_ephemeral_policy",
        "miss_cache_disabled",
        "expired_ttl",
        "corrupt_validation_failed",
        "corrupt_hmac_failed",
        "rejected_contract_mismatch",
    ]
    summarizer_id: str
    schema_version: str
    redaction_policy_id: str


class OutputCacheEvent(BaseModel):
    cache_key_prefix: str
    status: Literal["hit", "miss", "expired", "corrupt", "disabled"]
    reason: Literal[
        "output_hit_same_render_key",
        "output_miss",
        "output_miss_mode_changed",
        "output_miss_template_changed",
        "output_expired_ttl",
        "output_corrupt_validation_failed",
        "output_read_skipped_policy",
        "output_disabled",
        "output_disabled_normalization_unknowns",
    ]


class PipelineStats(BaseModel):
    input_documents: int = 0
    output_cache_hit: bool = False
    output_cache_expired: int = 0
    document_cache_hits: int = 0
    document_cache_misses: int = 0
    document_cache_expired: int = 0
    document_cache_corrupt: int = 0
    summarizer_calls: int = 0
    rendered_mode: str = "brief"
    cache_keys: dict[str, str] = Field(default_factory=dict)
    cache_policy: str = "read_write"
    entries_pruned: int = 0
    bytes_pruned: int = 0
    evidence_validation_errors: int = 0
    pii_redactions: int = 0
    delete_on_exit_applied: bool = False
    document_cache_events: list[DocumentCacheEvent] = Field(default_factory=list)
    output_cache_event: OutputCacheEvent | None = None


class PipelineResult(BaseModel):
    output: str
    summaries: list[DocumentSummaryState]
    stats: PipelineStats
