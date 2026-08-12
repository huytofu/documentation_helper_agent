"""On-disk cache for Firecrawl scrape results (skip re-crawl on reingest)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document

from ingestion.documents import build_firecrawl_document

logger = logging.getLogger(__name__)


def default_cache_dir() -> Path:
    return Path.cwd() / ".cache" / "firecrawl"


def url_hash(urls: list[str]) -> str:
    """SHA-256 of URLs joined with newlines in list order."""
    payload = "\n".join(urls).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cache_path(framework: str, *, cache_dir: Optional[Path] = None) -> Path:
    base = cache_dir if cache_dir is not None else default_cache_dir()
    return base / f"{framework}.json"


def save_cache(
    framework: str,
    urls: list[str],
    docs: list[Document],
    *,
    cache_dir: Optional[Path] = None,
) -> Path:
    """Write crawl cache for a framework. Creates parent directories."""
    path = cache_path(framework, cache_dir=cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    documents = []
    for doc in docs:
        meta = doc.metadata or {}
        documents.append(
            {
                "content": doc.page_content or "",
                "url": str(meta.get("source") or ""),
                "framework": str(meta.get("framework") or framework),
            }
        )

    payload = {
        "framework": framework,
        "url_hash": url_hash(urls),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote Firecrawl cache for %s (%d docs) → %s", framework, len(docs), path)
    return path


def load_cache(
    framework: str,
    urls: list[str],
    *,
    cache_dir: Optional[Path] = None,
) -> Optional[list[Document]]:
    """
    Load Documents from cache if present and url_hash matches.

    Returns None on miss, hash mismatch, or corrupt/unreadable file.
    """
    path = cache_path(framework, cache_dir=cache_dir)
    if not path.is_file():
        return None

    expected = url_hash(urls)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Corrupt Firecrawl cache for %s (%s): %s", framework, path, exc)
        return None

    if not isinstance(payload, dict):
        logger.warning("Corrupt Firecrawl cache for %s: root not an object", framework)
        return None

    stored_hash = payload.get("url_hash")
    if stored_hash != expected:
        logger.warning(
            "Firecrawl cache stale for %s (url list changed); will re-crawl",
            framework,
        )
        return None

    raw_docs = payload.get("documents")
    if not isinstance(raw_docs, list):
        logger.warning("Corrupt Firecrawl cache for %s: documents not a list", framework)
        return None

    docs: list[Document] = []
    for item in raw_docs:
        if not isinstance(item, dict):
            continue
        content = item.get("content") or ""
        url = item.get("url") or ""
        fw = item.get("framework") or framework
        if not url:
            continue
        docs.append(build_firecrawl_document(str(content), str(url), str(fw)))

    logger.info("Loaded Firecrawl cache for %s (%d docs) from %s", framework, len(docs), path)
    return docs
