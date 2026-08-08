"""Clear Pinecone namespaces ahead of reingestion."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_index() -> tuple[Any, str]:
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not api_key or not index_name:
        raise ValueError(
            "Pinecone credentials are required. "
            "Set PINECONE_API_KEY and PINECONE_INDEX_NAME."
        )
    from pinecone import Pinecone

    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name), index_name


def clear_namespaces(*, is_all: bool, namespaces: list[str]) -> list[str]:
    """
    Delete vectors from Pinecone namespaces.

    When ``is_all`` is True, every namespace present on the index is cleared.
    Otherwise ``namespaces`` is deleted as listed.
    """
    index, index_name = _get_index()

    if is_all:
        stats = index.describe_index_stats()
        ns_map = getattr(stats, "namespaces", None)
        if ns_map is None and isinstance(stats, dict):
            ns_map = stats.get("namespaces")
        ns_map = ns_map or {}
        targets = sorted(ns_map.keys())
        logger.info(
            "Clearing ALL namespaces on index %s: %s",
            index_name,
            targets or "(none)",
        )
    else:
        targets = list(namespaces)
        logger.info("Clearing namespaces on index %s: %s", index_name, targets)

    cleared: list[str] = []
    for ns in targets:
        try:
            index.delete(delete_all=True, namespace=ns)
            cleared.append(ns)
            logger.info("Cleared namespace %s", ns)
        except Exception as exc:
            logger.error(
                "Failed clearing namespace %s after successful clears %s: %s",
                ns,
                cleared,
                exc,
            )
            raise RuntimeError(
                f"Failed clearing namespace {ns!r} on index {index_name!r}: {exc}"
            ) from exc
    return cleared
