"""Documentation ingestion package (Firecrawl + chub → Pinecone)."""

from __future__ import annotations

from typing import Any

__all__ = ["ingest_documents", "run_ingestion"]


def __getattr__(name: str) -> Any:
    if name == "ingest_documents":
        from ingestion.documents import ingest_documents

        return ingest_documents
    if name == "run_ingestion":
        from ingestion.pipeline import run_ingestion

        return run_ingestion
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
