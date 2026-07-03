from __future__ import annotations

import time
import shutil
from dataclasses import dataclass
from pathlib import Path

from .llm import estimate_tokens
from .models import CacheConfig, DocumentInput, DocumentSection, DocumentSummaryState
from .normalize import split_into_sections
from .pipeline import BriefingPipeline
from .summarizers import BaseSummarizer, RuleBasedExtractiveSummarizer, contains_any, extract_metrics, split_section_sentences


DEFAULT_BENCHMARK_MODES = ["brief", "digest", "executive", "action_items", "debug"]
BENCHMARK_CACHE_NAMESPACES = ("document_summaries", "rendered_outputs")


@dataclass(frozen=True)
class BenchmarkScenario:
    name: str
    documents: list[DocumentInput]
    mode: str


class MeteredSummarizer(BaseSummarizer):
    """Wrap a summarizer and record cache-miss summarization work."""

    def __init__(self, inner: BaseSummarizer):
        self.inner = inner
        self.summarizer_id = inner.summarizer_id
        self.calls = 0
        self.input_tokens_estimate = 0

    def summarize(
        self,
        document: DocumentInput,
        sections: list[DocumentSection],
        content_fingerprint: str,
    ) -> DocumentSummaryState:
        self.calls += 1
        text = "\n\n".join(section.text for section in sections) if sections else (document.text or "")
        self.input_tokens_estimate += estimate_tokens(text)
        return self.inner.summarize(document, sections, content_fingerprint)


def build_standard_scenarios(
    base_documents: list[DocumentInput],
    incremental_documents: list[DocumentInput] | None = None,
    modes: list[str] | None = None,
) -> list[BenchmarkScenario]:
    modes = modes or DEFAULT_BENCHMARK_MODES
    if not modes:
        raise ValueError("At least one rendering mode is required.")

    first_mode = modes[0]
    scenarios = [
        BenchmarkScenario(name=f"cold {first_mode} base", documents=base_documents, mode=first_mode),
        BenchmarkScenario(name=f"same {first_mode} base", documents=base_documents, mode=first_mode),
    ]
    scenarios.extend(
        BenchmarkScenario(name=f"rerender {mode} base", documents=base_documents, mode=mode)
        for mode in modes[1:]
    )

    if incremental_documents:
        combined = [*base_documents, *incremental_documents]
        scenarios.append(BenchmarkScenario(name=f"add incremental {first_mode}", documents=combined, mode=first_mode))
        scenarios.append(BenchmarkScenario(name="rerender debug combined", documents=combined, mode="debug"))

    return scenarios


def run_benchmark(
    scenarios: list[BenchmarkScenario],
    cache_dir: str | Path,
    summarizer: BaseSummarizer | None = None,
    fresh_cache: bool = False,
) -> dict:
    cache_path = Path(cache_dir)
    if fresh_cache:
        clear_benchmark_cache(cache_path)

    metered = MeteredSummarizer(summarizer or RuleBasedExtractiveSummarizer())
    cache_config = CacheConfig(
        cache_dir=str(cache_path),
        output_cache=True,
        document_ttl_seconds=None,
        output_ttl_seconds=None,
    )
    pipeline = BriefingPipeline(cache_config=cache_config, summarizer=metered)

    rows = []
    naive_tokens = 0
    cacheaware_tokens = 0
    for scenario in scenarios:
        scenario_naive_tokens = sum(estimate_document_summarizer_input_tokens(document) for document in scenario.documents)
        naive_tokens += scenario_naive_tokens

        calls_before = metered.calls
        tokens_before = metered.input_tokens_estimate
        started_at = time.perf_counter()
        result = pipeline.run(scenario.documents, mode=scenario.mode, use_output_cache=True)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        scenario_calls = metered.calls - calls_before
        scenario_cacheaware_tokens = metered.input_tokens_estimate - tokens_before
        cacheaware_tokens += scenario_cacheaware_tokens

        rows.append(
            {
                "scenario": scenario.name,
                "mode": scenario.mode,
                "documents": len(scenario.documents),
                "input_token_estimate_if_no_cache": scenario_naive_tokens,
                "cacheaware_summarizer_input_token_estimate": scenario_cacheaware_tokens,
                "output_cache_hit": result.stats.output_cache_hit,
                "document_cache_hits": result.stats.document_cache_hits,
                "document_cache_misses": result.stats.document_cache_misses,
                "document_cache_corrupt": result.stats.document_cache_corrupt,
                "summarizer_calls": scenario_calls,
                "evidence_validation_errors": result.stats.evidence_validation_errors,
                "elapsed_ms": round(elapsed_ms, 2),
                "output_chars": len(result.output),
                "quality": assess_quality(scenario.documents, result.summaries),
            }
        )

    saved_tokens = naive_tokens - cacheaware_tokens
    return {
        "cache_dir": str(cache_path),
        "scenario_count": len(scenarios),
        "naive_resummarize_every_run_input_tokens_est": naive_tokens,
        "cacheaware_cache_miss_only_input_tokens_est": cacheaware_tokens,
        "estimated_tokens_saved": saved_tokens,
        "estimated_savings_percent": round((saved_tokens / naive_tokens) * 100, 2) if naive_tokens else 0,
        "total_summarizer_calls": sum(row["summarizer_calls"] for row in rows),
        "total_document_cache_hits": sum(row["document_cache_hits"] for row in rows),
        "total_document_cache_misses": sum(row["document_cache_misses"] for row in rows),
        "quality_warning_rows": sum(1 for row in rows if row["quality"]["warnings"]),
        "quality_warning_count": sum(len(row["quality"]["warnings"]) for row in rows),
        "quality_unevaluated_rows": sum(1 for row in rows if not row["quality"]["evaluated"]),
        "rows": rows,
    }


def clear_benchmark_cache(cache_path: Path) -> None:
    if not cache_path.exists():
        return
    if not cache_path.is_dir():
        raise ValueError("Benchmark cache path must be a directory when fresh_cache=True.")

    for namespace in BENCHMARK_CACHE_NAMESPACES:
        namespace_path = cache_path / namespace
        if namespace_path.is_dir():
            shutil.rmtree(namespace_path)
        elif namespace_path.exists():
            namespace_path.unlink()


def estimate_document_summarizer_input_tokens(document: DocumentInput) -> int:
    sections = split_into_sections(document.text or "")
    text = "\n\n".join(section.text for section in sections) if sections else (document.text or "")
    return estimate_tokens(text)


def assess_quality(documents: list[DocumentInput], summaries: list[DocumentSummaryState]) -> dict:
    source_candidates = count_source_candidates(documents)
    extracted = count_extracted_items(summaries)
    if not summaries:
        return {
            "evaluated": False,
            "source_candidates": source_candidates,
            "extracted": extracted,
            "coverage_percent": {name: None for name in source_candidates},
            "warnings": [],
        }

    coverage = {
        name: coverage_percent(extracted[name], source_candidates[name])
        for name in source_candidates
    }
    warnings = [
        f"{name} coverage {extracted[name]}/{source_candidates[name]} ({coverage[name]}%)"
        for name in ("actions", "decisions", "risks", "metrics")
        if source_candidates[name] and extracted[name] < source_candidates[name]
    ]
    return {
        "evaluated": True,
        "source_candidates": source_candidates,
        "extracted": extracted,
        "coverage_percent": coverage,
        "warnings": warnings,
    }


def count_source_candidates(documents: list[DocumentInput]) -> dict[str, int]:
    counts = {"actions": 0, "decisions": 0, "risks": 0, "metrics": 0}
    for document in documents:
        sections = split_into_sections(document.text or "")
        text = "\n\n".join(section.text for section in sections) if sections else (document.text or "")
        sentences = split_section_sentences(sections, text)
        counts["actions"] += sum(1 for sentence in sentences if contains_any(sentence, RuleBasedExtractiveSummarizer.action_keywords))
        counts["decisions"] += sum(1 for sentence in sentences if contains_any(sentence, RuleBasedExtractiveSummarizer.decision_keywords))
        counts["risks"] += sum(1 for sentence in sentences if contains_any(sentence, RuleBasedExtractiveSummarizer.risk_keywords))
        counts["metrics"] += len(extract_metrics(sentences))
    return counts


def count_extracted_items(summaries: list[DocumentSummaryState]) -> dict[str, int]:
    return {
        "actions": sum(len(summary.actions) for summary in summaries),
        "decisions": sum(len(summary.decisions) for summary in summaries),
        "risks": sum(len(summary.risks) for summary in summaries),
        "metrics": sum(len(summary.metrics) for summary in summaries),
    }


def coverage_percent(extracted: int, candidates: int) -> float | None:
    if not candidates:
        return None
    return round((min(extracted, candidates) / candidates) * 100, 2)
