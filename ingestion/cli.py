"""CLI entrypoint for documentation ingestion."""

from __future__ import annotations

import argparse
import logging
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest documentation into Pinecone via Firecrawl and/or chub.",
    )
    parser.add_argument(
        "--source",
        choices=("firecrawl", "chub", "all"),
        default=None,
        help="Which source(s) to ingest (default: all when ingesting)",
    )
    parser.add_argument(
        "--framework",
        default=None,
        help=(
            "Namespace selector: 'all' or comma-separated known namespaces "
            "(langgraph,llamaindex,smolagents,copilotkit,chub). "
            "Required with --clear."
        ),
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear Pinecone namespace(s) before optional ingest",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip interactive confirmation for --clear",
    )
    parser.add_argument(
        "--match-env",
        action="store_true",
        help="For chub get: prefer versions matching installed deps (optional)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )
    return parser


def _confirm_clear(*, is_all: bool, namespaces: list[str]) -> bool:
    index_name = os.getenv("PINECONE_INDEX_NAME") or "(PINECONE_INDEX_NAME unset)"
    if is_all:
        target = "ALL namespaces on the index"
    else:
        target = ", ".join(namespaces)
    print(f"About to clear Pinecone index {index_name!r}: {target}")
    answer = input("Type 'yes' to continue: ").strip()
    return answer == "yes"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    source_explicit = args.source is not None
    is_all = False
    clear_namespaces_list: list[str] = []
    frameworks: list[str] | None = None

    if args.clear and args.framework is None:
        print("error: --clear requires --framework", file=sys.stderr)
        return 2

    if args.framework is not None:
        from ingestion.framework_arg import parse_framework_arg

        try:
            is_all, clear_namespaces_list = parse_framework_arg(args.framework)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        frameworks = None if is_all else clear_namespaces_list

    if args.clear:
        if not args.yes and not _confirm_clear(
            is_all=is_all, namespaces=clear_namespaces_list
        ):
            print("Aborted; no namespaces cleared.", file=sys.stderr)
            return 1

        from ingestion.clear import clear_namespaces

        try:
            cleared = clear_namespaces(
                is_all=is_all, namespaces=clear_namespaces_list
            )
        except (ValueError, RuntimeError) as exc:
            logger.error("Clear failed: %s", exc)
            print(f"error: clear failed: {exc}", file=sys.stderr)
            return 1

        print(f"Cleared {len(cleared)} namespace(s): {', '.join(cleared) or '(none)'}")
        if not source_explicit:
            return 0

    from ingestion.pipeline import run_ingestion

    results = run_ingestion(
        source=args.source or "all",
        frameworks=frameworks,
        match_env=args.match_env,
    )

    print("\nIngestion summary:")
    for source_name, counts in results.items():
        print(f"  {source_name}:")
        if not counts:
            print("    (no documents)")
            continue
        for ns, n in counts.items():
            print(f"    {ns}: {n} source documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
