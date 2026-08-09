"""Long-term LangGraph Store (app-level memory).

Used for the chub package catalog that survives across threads and image rebuilds
when backed by Redis.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Optional, Tuple, Union

from dotenv import load_dotenv
from langgraph.store.base import BaseStore, Item
from langgraph.store.memory import InMemoryStore

load_dotenv()

logger = logging.getLogger("graph.stores")

# App-level namespace for packages indexed in the Pinecone `chub` namespace.
CHUB_PACKAGES_NS: Tuple[str, str, str] = ("kb", "chub", "packages")

STORE_TYPE = os.getenv("STORE_TYPE", "").lower().strip()
REDIS_URL = os.getenv("REDIS_URL")

_store: Optional[BaseStore] = None
_store_setup_done = False


def get_store() -> BaseStore:
    """Return process-level BaseStore (Redis when configured, else InMemoryStore)."""
    global _store
    if _store is not None:
        return _store

    # Redis when REDIS_URL is set, unless STORE_TYPE=memory forces local-only.
    use_redis = bool(REDIS_URL) and STORE_TYPE != "memory"

    if use_redis and REDIS_URL:
        try:
            from redis import Redis
            from langgraph.store.redis import RedisStore

            client = Redis.from_url(REDIS_URL)
            # RedisStore is the process-lifetime twin of AsyncRedisStore (same package).
            # Sync put() is required from ingest_documents; asearch() still works in nodes.
            store = RedisStore(conn=client, store_prefix="lg:store")
            _store = store
            logger.info("Using RedisStore for long-term memory")
            return _store
        except Exception:
            logger.exception(
                "Failed to create RedisStore; falling back to InMemoryStore"
            )

    _store = InMemoryStore()
    logger.info("Using InMemoryStore for long-term memory")
    return _store


def ensure_store_setup(store: Optional[BaseStore] = None) -> None:
    """Create Redis indices if needed (idempotent). Safe no-op for InMemoryStore."""
    global _store_setup_done
    store = store or get_store()
    if _store_setup_done:
        return
    setup = getattr(store, "setup", None)
    if callable(setup):
        try:
            setup()
            logger.info("Store setup completed")
        except Exception:
            logger.exception("Store setup failed")
            return
    _store_setup_done = True


async def aensure_store_setup(store: Optional[BaseStore] = None) -> None:
    """Async setup for stores that expose async setup (e.g. AsyncRedisStore)."""
    global _store_setup_done
    store = store or get_store()
    if _store_setup_done:
        return
    setup = getattr(store, "setup", None)
    if callable(setup):
        try:
            result = setup()
            if hasattr(result, "__await__"):
                await result
            logger.info("Store setup completed")
        except Exception:
            logger.exception("Store setup failed")
            return
    _store_setup_done = True


def remember_chub_package(
    doc_id: str,
    title: Optional[str] = None,
    *,
    store: Optional[BaseStore] = None,
) -> None:
    """Upsert a chub package into long-term memory. Never raises."""
    if not doc_id or not str(doc_id).strip():
        return
    doc_id = str(doc_id).strip()
    value = {"doc_id": doc_id, "title": (title or doc_id)}
    try:
        s = store or get_store()
        ensure_store_setup(s)
        s.put(CHUB_PACKAGES_NS, doc_id, value)
        logger.info("Remembered chub package %s", doc_id)
    except Exception:
        logger.exception("Failed to remember chub package %s", doc_id)


def format_chub_packages_for_prompt(
    items: Union[Iterable[Item], Iterable[Any], None],
) -> str:
    """Format store search hits as a compact prompt block."""
    if not items:
        return "(none indexed yet)"

    lines: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = getattr(item, "value", None)
        if not isinstance(value, dict):
            if isinstance(item, dict):
                value = item
            else:
                continue
        doc_id = str(value.get("doc_id") or getattr(item, "key", "") or "").strip()
        title = str(value.get("title") or doc_id).strip()
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        if title and title != doc_id:
            lines.append(f"- {doc_id} ({title})")
        else:
            lines.append(f"- {doc_id}")

    return "\n".join(lines) if lines else "(none indexed yet)"


__all__ = [
    "CHUB_PACKAGES_NS",
    "get_store",
    "ensure_store_setup",
    "aensure_store_setup",
    "remember_chub_package",
    "format_chub_packages_for_prompt",
]
