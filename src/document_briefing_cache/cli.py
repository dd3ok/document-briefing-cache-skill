from __future__ import annotations

import argparse
import json
import sys

from .benchmark import build_standard_scenarios, run_benchmark
from .cache import merge_operation_results
from .llm import LLMConfig
from .models import CacheConfig, DocumentInput
from .normalize import load_path_to_documents, split_documents_into_incident_records, split_documents_into_section_documents
from .pipeline import BriefingPipeline
from .summarizers import OpenAIStructuredSummarizer, RuleBasedExtractiveSummarizer


def build_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render cached document briefings from broad document inputs.")
    add_run_arguments(parser)
    return parser


def add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", "-i", action="append", required=True, help="Input file path. Can be repeated.")
    parser.add_argument("--mode", default="brief", choices=["brief", "executive", "action_items", "digest", "debug"])
    parser.add_argument("--audience", default="general")
    parser.add_argument("--locale", default="ko-KR")
    parser.add_argument("--cache-dir", default=".cache")
    parser.add_argument("--summary-mode", default="rules", choices=["rules", "openai"])
    parser.add_argument("--split-records", default="none", choices=["none", "incident"], help="Split stable operational records before caching.")
    parser.add_argument("--split-input-sections", action="store_true", help="Split multi-section inputs into section-level documents before caching.")
    parser.add_argument("--openai-model", default=None)
    parser.add_argument("--llm-timeout", type=float, default=60.0)
    parser.add_argument("--llm-max-retries", type=int, default=2)
    parser.add_argument("--llm-max-input-tokens", type=int, default=12000)
    parser.add_argument("--llm-max-output-tokens", type=int, default=4000)
    parser.add_argument("--no-output-cache", action="store_true")
    parser.add_argument("--cache-policy", default="read_write", choices=["read_write", "read_only", "refresh", "bypass", "ephemeral", "ttl", "persistent"])
    parser.add_argument("--sensitive", action="store_true", help="Alias for ephemeral cache, no output cache, PII redaction, and delete-on-exit for created files.")
    parser.add_argument("--document-ttl", default="30d")
    parser.add_argument("--output-ttl", default="24h")
    parser.add_argument("--prune-on-start", action="store_true")
    parser.add_argument("--prune-on-exit", action="store_true")
    parser.add_argument("--delete-on-exit", default="none", choices=["none", "created", "all"])
    parser.add_argument("--redact-pii", action="store_true", help="Redact basic contact PII before summarization and cache writes.")
    parser.add_argument("--redact-secrets", action="store_true", help="Best-effort redaction for tokens, API keys, webhook URLs, and card-like values.")
    parser.add_argument("--cache-hmac-secret-env", default=None, help="Environment variable containing the cache HMAC signing secret.")
    parser.add_argument("--show-stats", action="store_true")
    parser.add_argument("--explain-cache", action="store_true", help="Print per-document cache hit/miss reasons after rendering.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render cached document briefings from broad document inputs.")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Render cached document briefings.")
    add_run_arguments(run_parser)

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark repeated rendering and document cache reuse.")
    benchmark_parser.add_argument("--input", "-i", action="append", required=True, help="Base input file path. Can be repeated.")
    benchmark_parser.add_argument("--incremental-input", action="append", default=[], help="Additional input file path for the incremental phase.")
    benchmark_parser.add_argument("--mode", action="append", default=None, choices=["brief", "executive", "action_items", "digest", "debug"])
    benchmark_parser.add_argument("--cache-dir", default=".cache/benchmark")
    benchmark_parser.add_argument("--fresh", action="store_true", help="Clear the benchmark cache directory before running.")
    benchmark_parser.add_argument("--summary-mode", default="rules", choices=["rules", "openai"])
    benchmark_parser.add_argument("--split-records", default="none", choices=["none", "incident"], help="Split stable operational records before benchmarking.")
    benchmark_parser.add_argument("--split-input-sections", action="store_true", help="Split multi-section inputs into section-level documents before benchmarking.")
    benchmark_parser.add_argument("--openai-model", default=None)
    benchmark_parser.add_argument("--llm-timeout", type=float, default=60.0)
    benchmark_parser.add_argument("--llm-max-retries", type=int, default=2)
    benchmark_parser.add_argument("--llm-max-input-tokens", type=int, default=12000)
    benchmark_parser.add_argument("--llm-max-output-tokens", type=int, default=4000)
    benchmark_parser.add_argument("--json", action="store_true")

    cache_parser = subparsers.add_parser("cache", help="Inspect or clean cache data.")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)

    stats_parser = cache_subparsers.add_parser("stats", help="Show cache statistics.")
    stats_parser.add_argument("--cache-dir", default=".cache")
    stats_parser.add_argument("--cache-hmac-secret-env", default=None)
    stats_parser.add_argument("--json", action="store_true")

    prune_parser = cache_subparsers.add_parser("prune", help="Delete expired or older cache entries.")
    prune_parser.add_argument("--cache-dir", default=".cache")
    prune_parser.add_argument("--cache-hmac-secret-env", default=None)
    prune_parser.add_argument("--older-than", default=None)
    prune_parser.add_argument("--layer", default="all", choices=["all", "document_summaries", "rendered_outputs"])
    prune_parser.add_argument("--dry-run", action="store_true")
    prune_parser.add_argument("--json", action="store_true")

    clear_parser = cache_subparsers.add_parser("clear", help="Clear cache entries.")
    clear_parser.add_argument("--cache-dir", default=".cache")
    clear_parser.add_argument("--cache-hmac-secret-env", default=None)
    clear_parser.add_argument("--layer", default="all", choices=["all", "document_summaries", "rendered_outputs"])
    clear_parser.add_argument("--yes", action="store_true")
    clear_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv and argv[0] not in {"run", "benchmark", "cache"} and argv[0] not in {"-h", "--help"}:
        return run_main(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_with_args(args)
    if args.command == "benchmark":
        return benchmark_main(args)
    if args.command == "cache":
        return cache_main(args)
    parser.print_help()
    return 2


def run_main(argv: list[str] | None = None) -> int:
    parser = build_run_parser()
    args = parser.parse_args(argv)
    return run_with_args(args)


def is_http_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def run_with_args(args: argparse.Namespace) -> int:
    apply_sensitive_alias(args)
    for input_path in args.input:
        if is_http_url(input_path):
            sys.stderr.write(
                "URL fetching is not supported by --input. "
                "Pass a local file path, or include source/url metadata inside a JSON/XML payload.\n"
            )
            return 2

    documents = load_documents_from_paths(args.input)
    documents = split_documents_for_args(documents, args)

    if args.summary_mode == "rules":
        summarizer = RuleBasedExtractiveSummarizer()
    else:
        summarizer = OpenAIStructuredSummarizer(
            model=args.openai_model,
            llm_config=LLMConfig(
                timeout_seconds=args.llm_timeout,
                max_retries=args.llm_max_retries,
                max_input_tokens=args.llm_max_input_tokens,
                max_output_tokens=args.llm_max_output_tokens,
            ),
        )
    cache_config = CacheConfig(
        cache_dir=args.cache_dir,
        policy=args.cache_policy,
        output_cache=not args.no_output_cache,
        document_ttl_seconds=parse_duration_seconds(args.document_ttl),
        output_ttl_seconds=parse_duration_seconds(args.output_ttl),
        prune_on_start=args.prune_on_start,
        prune_on_exit=args.prune_on_exit,
        delete_on_exit=args.delete_on_exit,
        cache_hmac_secret_env=args.cache_hmac_secret_env,
        redact_pii=args.redact_pii,
        redact_secrets=getattr(args, "redact_secrets", False),
        sensitive_mode=getattr(args, "sensitive", False),
    )
    pipeline = BriefingPipeline(cache_config=cache_config, summarizer=summarizer)
    result = pipeline.run(
        documents,
        mode=args.mode,
        audience=args.audience,
        locale=args.locale,
    )
    sys.stdout.write(result.output)
    if args.show_stats:
        sys.stdout.write("\n--- stats ---\n")
        sys.stdout.write(json.dumps(result.stats.model_dump(mode="json"), ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    if args.explain_cache:
        write_cache_explanation(result.stats)
    return 0


def apply_sensitive_alias(args: argparse.Namespace) -> None:
    if not getattr(args, "sensitive", False):
        return
    args.cache_policy = "ephemeral"
    args.no_output_cache = True
    args.redact_pii = True
    args.delete_on_exit = "created"


def benchmark_main(args: argparse.Namespace) -> int:
    for input_path in [*args.input, *args.incremental_input]:
        if is_http_url(input_path):
            sys.stderr.write(
                "URL fetching is not supported by benchmark inputs. "
                "Pass a local file path, or include source/url metadata inside a JSON/XML payload.\n"
            )
            return 2

    base_documents = load_documents_from_paths(args.input)
    incremental_documents = load_documents_from_paths(args.incremental_input)
    base_documents = split_documents_for_args(base_documents, args)
    incremental_documents = split_documents_for_args(incremental_documents, args)
    scenarios = build_standard_scenarios(
        base_documents=base_documents,
        incremental_documents=incremental_documents,
        modes=args.mode,
    )
    report = run_benchmark(
        scenarios,
        cache_dir=args.cache_dir,
        summarizer=build_summarizer_from_args(args),
        fresh_cache=args.fresh,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    else:
        write_benchmark_report(report)
    return 0


def load_documents_from_paths(paths: list[str] | None) -> list[DocumentInput]:
    if not paths:
        return []
    documents = []
    for input_path in paths:
        documents.extend(load_path_to_documents(input_path))
    return documents


def split_documents_for_args(documents: list[DocumentInput], args: argparse.Namespace) -> list[DocumentInput]:
    if args.split_records == "incident":
        documents = split_documents_into_incident_records(documents)
    if args.split_input_sections:
        documents = split_documents_into_section_documents(documents)
    return documents


def build_summarizer_from_args(args: argparse.Namespace):
    if args.summary_mode == "rules":
        return RuleBasedExtractiveSummarizer()
    return OpenAIStructuredSummarizer(
        model=args.openai_model,
        llm_config=LLMConfig(
            timeout_seconds=args.llm_timeout,
            max_retries=args.llm_max_retries,
            max_input_tokens=args.llm_max_input_tokens,
            max_output_tokens=args.llm_max_output_tokens,
        ),
    )


def write_benchmark_report(report: dict) -> None:
    sys.stdout.write("Document briefing cache benchmark\n")
    sys.stdout.write(f"cache_dir: {report['cache_dir']}\n")
    sys.stdout.write(f"scenarios: {report['scenario_count']}\n")
    sys.stdout.write(f"naive_input_tokens_est: {report['naive_resummarize_every_run_input_tokens_est']}\n")
    sys.stdout.write(f"cacheaware_input_tokens_est: {report['cacheaware_cache_miss_only_input_tokens_est']}\n")
    sys.stdout.write(f"estimated_tokens_saved: {report['estimated_tokens_saved']}\n")
    sys.stdout.write(f"estimated_savings_percent: {report['estimated_savings_percent']}\n")
    sys.stdout.write(f"quality_warning_rows: {report.get('quality_warning_rows', 0)}\n")
    sys.stdout.write(f"quality_warning_count: {report.get('quality_warning_count', 0)}\n")
    sys.stdout.write(f"quality_unevaluated_rows: {report.get('quality_unevaluated_rows', 0)}\n")
    sys.stdout.write("\n")
    for row in report["rows"]:
        quality_evaluated = row.get("quality", {}).get("evaluated", False)
        quality_warnings = len(row.get("quality", {}).get("warnings", []))
        sys.stdout.write(
            "- "
            f"{row['scenario']}: "
            f"calls={row['summarizer_calls']}, "
            f"hits={row['document_cache_hits']}, "
            f"misses={row['document_cache_misses']}, "
            f"out_hit={str(row['output_cache_hit']).lower()}, "
            f"quality_evaluated={str(quality_evaluated).lower()}, "
            f"quality_warnings={quality_warnings}, "
            f"cacheaware_tokens={row['cacheaware_summarizer_input_token_estimate']}, "
            f"elapsed_ms={row['elapsed_ms']}\n"
        )


def write_cache_explanation(stats) -> None:
    sys.stdout.write("\n## Cache explanation\n\n")
    sys.stdout.write("| Document | Fingerprint | Result | Reason |\n")
    sys.stdout.write("| --- | --- | --- | --- |\n")
    for event in stats.document_cache_events:
        sys.stdout.write(
            f"| {event.document_id} | {event.fingerprint_prefix} | {event.status} | {event.reason} |\n"
        )
    if not stats.document_cache_events:
        if stats.output_cache_hit:
            sys.stdout.write("| n/a | n/a | n/a | output cache hit before document cache lookup |\n")
        else:
            sys.stdout.write("| n/a | n/a | n/a | no document cache events recorded |\n")
    sys.stdout.write("\nOutput cache:\n")
    if stats.output_cache_event is None:
        sys.stdout.write("- result: n/a\n")
        sys.stdout.write("- reason: output_disabled\n")
    else:
        sys.stdout.write(f"- result: {stats.output_cache_event.status}\n")
        sys.stdout.write(f"- reason: {stats.output_cache_event.reason}\n")


def cache_main(args: argparse.Namespace) -> int:
    pipeline = BriefingPipeline(cache_config=CacheConfig(cache_dir=args.cache_dir, cache_hmac_secret_env=args.cache_hmac_secret_env))
    if args.cache_command == "stats":
        payload = pipeline.stats()
        write_payload(payload, as_json=args.json)
        return 0
    if args.cache_command == "prune":
        result = prune_layer(pipeline, args.layer, older_than_seconds=parse_duration_seconds(args.older_than), dry_run=args.dry_run)
        write_payload(result.__dict__, as_json=args.json)
        return 0
    if args.cache_command == "clear":
        if not args.yes:
            raise SystemExit("Refusing to clear cache without --yes.")
        result = clear_layer(pipeline, args.layer)
        write_payload(result.__dict__, as_json=args.json)
        return 0
    return 2


def prune_layer(pipeline: BriefingPipeline, layer: str, older_than_seconds: int | None, dry_run: bool):
    if layer == "document_summaries":
        return pipeline.document_cache.prune(older_than_seconds=older_than_seconds, dry_run=dry_run)
    if layer == "rendered_outputs":
        return pipeline.output_cache.prune(older_than_seconds=older_than_seconds, dry_run=dry_run)
    return pipeline.prune(older_than_seconds=older_than_seconds, dry_run=dry_run)


def clear_layer(pipeline: BriefingPipeline, layer: str):
    if layer == "document_summaries":
        return pipeline.document_cache.clear()
    if layer == "rendered_outputs":
        return pipeline.output_cache.clear()
    return merge_operation_results(pipeline.document_cache.clear(), pipeline.output_cache.clear())


def write_payload(payload, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(f"{payload}\n")


def parse_duration_seconds(value: str | None) -> int | None:
    if value is None or value in {"never", "forever", "none"}:
        return None
    text = str(value).strip().lower()
    if text in {"0", "0s", "off"}:
        return 0
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = text[-1]
    if unit in multipliers:
        return int(float(text[:-1]) * multipliers[unit])
    return int(float(text))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
