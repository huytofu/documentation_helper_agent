"""Firecrawl-based documentation scraping."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from ingestion.documents import build_firecrawl_document
from langchain_core.documents import Document

load_dotenv()
logger = logging.getLogger(__name__)


def scrape_urls(
    framework: str,
    urls: list[str],
    *,
    batch_size: int = 10,
    batch_delay_seconds: int = 60,
    api_key: Optional[str] = None,
) -> list[Document]:
    """Scrape URLs with Firecrawl and return Documents."""
    if not urls:
        logger.info("Skipping %s: empty URL list", framework)
        return []

    key = api_key or os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("FIRECRAWL_API_KEY is required for Firecrawl ingestion")

    app = FirecrawlApp(api_key=key)
    docs: list[Document] = []
    successes = 0
    failures = 0
    url_count = len(urls)

    for i in range(0, url_count, batch_size):
        batch = urls[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (url_count + batch_size - 1) // batch_size
        logger.info(
            "Processing %s batch %d/%d (%d URLs)",
            framework,
            batch_num,
            total_batches,
            len(batch),
        )

        for url in batch:
            logger.info("FireCrawling %s", url)
            try:
                # scrape_url returns response["data"] on success (dict with markdown),
                # and raises on API/HTTP failure — there is no top-level success flag.
                result = app.scrape_url(url, params={"formats": ["markdown"]})
                if isinstance(result, dict):
                    content = result.get("markdown") or ""
                else:
                    content = getattr(result, "markdown", None) or ""
                if content.strip():
                    docs.append(build_firecrawl_document(content, url, framework))
                    successes += 1
                else:
                    failures += 1
                    logger.warning("Empty markdown for %s", url)
            except Exception as exc:  # noqa: BLE001 — continue batch on scrape errors
                failures += 1
                logger.error("Error loading %s: %s", url, exc)

        if i + batch_size < url_count:
            logger.info(
                "Waiting %d seconds before next batch...", batch_delay_seconds
            )
            time.sleep(batch_delay_seconds)

    logger.info(
        "%s Firecrawl done: %d ok, %d failed, %d documents",
        framework,
        successes,
        failures,
        len(docs),
    )
    return docs
