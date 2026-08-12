"""Orchestrate Firecrawl and/or chub ingestion into Pinecone."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ingestion.chub_source import load_chub_documents
from ingestion.documents import ingest_by_framework, ingest_documents
from ingestion.firecrawl_cache import load_cache, save_cache
from ingestion.firecrawl_source import scrape_urls
from ingestion.urls import FRAMEWORK_URLS

logger = logging.getLogger(__name__)


def run_firecrawl_ingestion(
    *,
    frameworks: Optional[list[str]] = None,
    skip_empty: bool = True,
    refresh: bool = False,
    cache_dir: Optional[Path] = None,
) -> dict[str, int]:
    """Scrape (or load cache) and ingest Firecrawl URL corpora."""
    selected = frameworks or list(FRAMEWORK_URLS.keys())
    totals: dict[str, int] = {}

    for framework in selected:
        urls = FRAMEWORK_URLS.get(framework, [])
        if skip_empty and not urls:
            logger.info("Skipping empty Firecrawl list for %s", framework)
            continue

        docs = None
        if not refresh:
            docs = load_cache(framework, urls, cache_dir=cache_dir)

        if docs is None:
            docs = scrape_urls(framework, urls)
            if docs:
                save_cache(framework, urls, docs, cache_dir=cache_dir)
        else:
            logger.info(
                "Using cached Firecrawl docs for %s (%d documents)",
                framework,
                len(docs),
            )

        if docs:
            ok = ingest_documents(framework, docs)
            totals[framework] = len(docs) if ok else 0
        else:
            totals[framework] = 0
    return totals


def run_chub_ingestion(
    *,
    match_env: bool = False,
    namespace_filter: Optional[list[str]] = None,
) -> dict[str, int]:
    """Fetch pinned chub docs and ingest into mapped namespaces."""
    docs = load_chub_documents(
        match_env=match_env,
        namespace_filter=namespace_filter,
    )
    if not docs:
        return {}
    return ingest_by_framework(docs)


def run_ingestion(
    *,
    source: str = "all",
    frameworks: Optional[list[str]] = None,
    match_env: bool = False,
    refresh: bool = False,
) -> dict[str, dict[str, int]]:
    """
    Run ingestion for the requested source(s).

    source: firecrawl | chub | all
    refresh: force Firecrawl re-crawl (ignore cache)
    """
    results: dict[str, dict[str, int]] = {}
    source = source.lower().strip()

    if source in ("firecrawl", "all"):
        logger.info("=== Firecrawl ingestion ===")
        results["firecrawl"] = run_firecrawl_ingestion(
            frameworks=frameworks,
            refresh=refresh,
        )

    if source in ("chub", "all"):
        logger.info("=== Chub ingestion ===")
        results["chub"] = run_chub_ingestion(
            match_env=match_env,
            namespace_filter=frameworks,
        )

    if source not in ("firecrawl", "chub", "all"):
        raise ValueError(f"Unknown source: {source} (use firecrawl|chub|all)")

    return results
