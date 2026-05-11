from __future__ import annotations

import argparse
import json
import sys

from .cache import merge_operation_results
from .models import CacheConfig
from .normalize import load_path_to_documents
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
    parser.add_argument("--no-output-cache", action="store_true")
    parser.add_argument("--cache-policy", default="read_write", choices=["read_write", "read_only", "refresh", "bypass", "ephemeral", "ttl", "persistent"])
    parser.add_argument("--document-ttl", default="30d")
    parser.add_argument("--output-ttl", default="24h")
    parser.add_argument("--prune-on-start", action="store_true")
    parser.add_argument("--prune-on-exit", action="store_true")
    parser.add_argument("--delete-on-exit", default="none", choices=["none", "created", "all"])
    parser.add_argument("--redact-pii", action="store_true", help="Redact basic contact PII before summarization and cache writes.")
    parser.add_argument("--cache-hmac-secret-env", default=None, help="Environment variable containing the cache HMAC signing secret.")
    parser.add_argument("--show-stats", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render cached document briefings from broad document inputs.")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Render cached document briefings.")
    add_run_arguments(run_parser)

    cache_parser = subparsers.add_parser("cache", help="Inspect or clean cache data.")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)

    stats_parser = cache_subparsers.add_parser("stats", help="Show cache statistics.")
    stats_parser.add_argument("--cache-dir", default=".cache")
    stats_parser.add_argument("--json", action="store_true")

    prune_parser = cache_subparsers.add_parser("prune", help="Delete expired or older cache entries.")
    prune_parser.add_argument("--cache-dir", default=".cache")
    prune_parser.add_argument("--older-than", default=None)
    prune_parser.add_argument("--layer", default="all", choices=["all", "document_summaries", "rendered_outputs"])
    prune_parser.add_argument("--dry-run", action="store_true")
    prune_parser.add_argument("--json", action="store_true")

    clear_parser = cache_subparsers.add_parser("clear", help="Clear cache entries.")
    clear_parser.add_argument("--cache-dir", default=".cache")
    clear_parser.add_argument("--layer", default="all", choices=["all", "document_summaries", "rendered_outputs"])
    clear_parser.add_argument("--yes", action="store_true")
    clear_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv and argv[0] not in {"run", "cache"} and argv[0] not in {"-h", "--help"}:
        return run_main(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_with_args(args)
    if args.command == "cache":
        return cache_main(args)
    parser.print_help()
    return 2


def run_main(argv: list[str] | None = None) -> int:
    parser = build_run_parser()
    args = parser.parse_args(argv)
    return run_with_args(args)


def run_with_args(args: argparse.Namespace) -> int:
    documents = []
    for input_path in args.input:
        documents.extend(load_path_to_documents(input_path))

    summarizer = RuleBasedExtractiveSummarizer() if args.summary_mode == "rules" else OpenAIStructuredSummarizer()
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
    return 0


def cache_main(args: argparse.Namespace) -> int:
    pipeline = BriefingPipeline(cache_config=CacheConfig(cache_dir=args.cache_dir))
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
