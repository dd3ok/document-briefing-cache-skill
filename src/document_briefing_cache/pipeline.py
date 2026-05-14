from __future__ import annotations

import os
from pathlib import Path

from .cache import JsonFileCache, merge_operation_results
from .evidence import validate_summary_evidence
from .hashing import (
    document_content_fingerprint,
    document_summary_cache_key,
    output_cache_key,
    stable_document_id,
)
from .models import DOCUMENT_SUMMARY_SCHEMA_VERSION, CacheConfig, DocumentInput, DocumentSummaryState, PipelineResult, PipelineStats
from .normalize import NORMALIZATION_UNKNOWNS_KEY, split_into_sections
from .privacy import redact_document_input, redaction_policy_id
from .render import TEMPLATE_VERSION, render_briefing
from .summarizers import BaseSummarizer, RuleBasedExtractiveSummarizer

SKILL_VERSION = "0.3.1"


class BriefingPipeline:
    def __init__(
        self,
        cache_dir: str | Path = ".cache",
        cache_config: CacheConfig | None = None,
        summarizer: BaseSummarizer | None = None,
        template_dir: str | Path | None = None,
        skill_version: str = SKILL_VERSION,
    ):
        self.cache_config = cache_config or CacheConfig(
            cache_dir=str(cache_dir),
            policy="read_write",
            output_cache=True,
            document_ttl_seconds=None,
            output_ttl_seconds=None,
        )
        self.cache_dir = Path(self.cache_config.cache_dir)
        self.summarizer = summarizer or RuleBasedExtractiveSummarizer()
        self.template_dir = template_dir
        self.skill_version = skill_version
        hmac_secret = self._cache_hmac_secret()
        self.document_cache = JsonFileCache(self.cache_dir, "document_summaries", hmac_secret=hmac_secret)
        self.output_cache = JsonFileCache(self.cache_dir, "rendered_outputs", hmac_secret=hmac_secret)

    def run(
        self,
        documents: list[DocumentInput],
        mode: str = "brief",
        audience: str = "general",
        locale: str = "ko-KR",
        use_output_cache: bool | None = None,
    ) -> PipelineResult:
        stats = PipelineStats(input_documents=len(documents), rendered_mode=mode, cache_policy=self.cache_config.policy)
        if self.cache_config.prune_on_start:
            pruned = self.prune()
            stats.entries_pruned += pruned.entries_deleted
            stats.bytes_pruned += pruned.bytes_deleted

        effective_output_cache = self.cache_config.output_cache if use_output_cache is None else use_output_cache
        has_normalization_unknowns = any(self._normalization_unknowns(document) for document in documents)
        if has_normalization_unknowns:
            effective_output_cache = False
        can_read = self.cache_config.policy not in {"bypass", "refresh", "ephemeral"}
        can_write = self.cache_config.policy not in {"bypass", "read_only", "ephemeral"}
        privacy_profile = redaction_policy_id(self.cache_config.redact_pii)

        out_key = output_cache_key(
            documents,
            mode=mode,
            audience=audience,
            locale=locale,
            skill_version=self.skill_version,
            template_version=TEMPLATE_VERSION,
            summarizer_id=self.summarizer.summarizer_id,
            redaction_policy_id=privacy_profile,
        )
        stats.cache_keys["output"] = out_key

        try:
            if effective_output_cache and can_read:
                output_result = self.output_cache.get_text_with_status(out_key, update_accessed=can_write)
                if output_result.status == "hit":
                    stats.output_cache_hit = True
                    return PipelineResult(output=output_result.value, summaries=[], stats=stats)
                if output_result.status == "expired":
                    stats.output_cache_expired += 1

            summaries: list[DocumentSummaryState] = []
            has_validation_errors = False
            for document in documents:
                fingerprint = document_content_fingerprint(document)
                summary_document = document
                if self.cache_config.redact_pii:
                    summary_document, redaction_count = redact_document_input(document)
                    stats.pii_redactions += redaction_count
                summary_key = document_summary_cache_key(
                    document,
                    fingerprint=fingerprint,
                    summarizer_id=self.summarizer.summarizer_id,
                    skill_version=self.skill_version,
                    redaction_policy_id=privacy_profile,
                )
                stats.cache_keys[f"document:{fingerprint[:12]}"] = summary_key
                cached: DocumentSummaryState | None = None
                status = "miss"
                if self.cache_config.document_cache and can_read:
                    cached, status = self.document_cache.get_model_with_status(summary_key, DocumentSummaryState, update_accessed=can_write)
                if cached is not None:
                    if not self._cached_summary_matches(summary_document, cached, fingerprint):
                        stats.document_cache_corrupt += 1
                        cached = None
                    else:
                        stats.document_cache_hits += 1
                        summaries.append(self._summary_with_normalization_unknowns(cached, summary_document))
                        continue
                if status == "corrupt":
                    stats.document_cache_corrupt += 1
                if status == "expired":
                    stats.document_cache_expired += 1

                stats.document_cache_misses += 1
                sections = split_into_sections(summary_document.text or "")
                summary = self.summarizer.summarize(summary_document, sections, fingerprint)
                stats.summarizer_calls += 1
                validation_errors = []
                if self.cache_config.validate_evidence:
                    validation_errors = validate_summary_evidence(summary, summary_document.text or "", sections=sections, raw=summary_document.raw)
                    stats.evidence_validation_errors += len(validation_errors)
                    if validation_errors:
                        has_validation_errors = True
                        summary.unknowns.extend(f"Evidence validation: {error}" for error in validation_errors)
                if self.cache_config.document_cache and can_write and not validation_errors:
                    self.document_cache.set_model(summary_key, summary, ttl_seconds=self._document_ttl_seconds())
                summaries.append(self._summary_with_normalization_unknowns(summary, summary_document))

            output = render_briefing(
                summaries,
                mode=mode,
                audience=audience,
                locale=locale,
                stats=stats,
                template_dir=self.template_dir,
            )
            if effective_output_cache and can_write and not has_validation_errors:
                self.output_cache.set_text(out_key, output, ttl_seconds=self._output_ttl_seconds())
            return PipelineResult(output=output, summaries=summaries, stats=stats)
        finally:
            if self.cache_config.prune_on_exit:
                self.prune()
            if self.cache_config.policy == "ephemeral" or self.cache_config.delete_on_exit == "created":
                self.clear_created()
                stats.delete_on_exit_applied = True
            elif self.cache_config.delete_on_exit == "all":
                self.clear()
                stats.delete_on_exit_applied = True

    def prune(self, older_than_seconds: int | None = None, dry_run: bool = False):
        return merge_operation_results(
            self.output_cache.prune(older_than_seconds=older_than_seconds, dry_run=dry_run),
            self.document_cache.prune(older_than_seconds=older_than_seconds, dry_run=dry_run),
        )

    def clear(self, dry_run: bool = False):
        return merge_operation_results(
            self.output_cache.clear(dry_run=dry_run),
            self.document_cache.clear(dry_run=dry_run),
        )

    def clear_created(self):
        return merge_operation_results(self.output_cache.clear_created(), self.document_cache.clear_created())

    def stats(self):
        return {
            "document_summaries": self.document_cache.stats(),
            "rendered_outputs": self.output_cache.stats(),
        }

    def _document_ttl_seconds(self) -> int | None:
        if self.cache_config.policy == "persistent":
            return None
        return self.cache_config.document_ttl_seconds

    def _output_ttl_seconds(self) -> int | None:
        if self.cache_config.policy == "persistent":
            return None
        return self.cache_config.output_ttl_seconds

    def _cache_hmac_secret(self) -> str | None:
        if not self.cache_config.cache_hmac_secret_env:
            return None
        secret = os.getenv(self.cache_config.cache_hmac_secret_env)
        if not secret:
            raise RuntimeError(f"Cache HMAC secret environment variable is not set: {self.cache_config.cache_hmac_secret_env}")
        return secret

    def _cached_summary_matches(self, document: DocumentInput, summary: DocumentSummaryState, fingerprint: str) -> bool:
        return (
            summary.schema_version == DOCUMENT_SUMMARY_SCHEMA_VERSION
            and summary.document_id == stable_document_id(document, fingerprint)
            and summary.content_fingerprint == fingerprint
            and summary.summarizer_id == self.summarizer.summarizer_id
        )

    def _summary_with_normalization_unknowns(self, summary: DocumentSummaryState, document: DocumentInput) -> DocumentSummaryState:
        normalization_unknowns = self._normalization_unknowns(document)
        if not normalization_unknowns:
            return summary
        run_summary = summary.model_copy(deep=True)
        for unknown in normalization_unknowns:
            if unknown not in run_summary.unknowns:
                run_summary.unknowns.append(unknown)
        return run_summary

    def _normalization_unknowns(self, document: DocumentInput) -> list[str]:
        normalization_unknowns = document.metadata.get(NORMALIZATION_UNKNOWNS_KEY, [])
        if not isinstance(normalization_unknowns, list):
            return []
        return [unknown for unknown in normalization_unknowns if isinstance(unknown, str)]
