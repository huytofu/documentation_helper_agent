"""CLI entrypoint for documentation ingestion."""

from __future__ import annotations

import argparse
import logging
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest documentation into Pinecone via Firecrawl and/or chub.",
    )
    parser.add_argument(
        "--source",
        choices=("firecrawl", "chub", "all"),
        default="all",
        help="Which source(s) to ingest (default: all)",
    )
    parser.add_argument(
        "--framework",
        action="append",
        dest="frameworks",
        help=(
            "Limit to namespace(s): llamaindex, smolagents, langgraph, "
            "copilotkit, chub. Repeatable."
        ),
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    from ingestion.pipeline import run_ingestion

    results = run_ingestion(
        source=args.source,
        frameworks=args.frameworks,
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
