"""Load curated docs from project chub pins (agentic-dev expert corpus)."""

from __future__ import annotations

import logging
from typing import Any, Collection, Optional

from langchain_core.documents import Document

from ingestion import chub_client
from ingestion.documents import build_chub_document
from ingestion.namespace_map import namespace_for_doc_id

logger = logging.getLogger(__name__)


def _pin_key(doc_id: str, lang: Optional[str]) -> tuple[str, str]:
    return (doc_id, (lang or "").lower())


def collect_targets() -> list[dict[str, Any]]:
    """Return ingest targets from `.chub/pins.yaml` only."""
    seen: set[tuple[str, str]] = set()
    targets: list[dict[str, Any]] = []

    for pin in chub_client.read_pins_yaml():
        doc_id = pin.get("id")
        if not doc_id:
            continue
        lang = pin.get("lang") or "python"
        key = _pin_key(doc_id, lang)
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            {
                "id": doc_id,
                "lang": lang,
                "version": pin.get("version"),
                "source": "pin",
                "reason": pin.get("reason"),
            }
        )

    return targets


def load_chub_documents(
    *,
    match_env: bool = False,
    namespace_filter: Optional[Collection[str]] = None,
) -> list[Document]:
    """Fetch pinned docs and convert to Documents."""
    targets = collect_targets()
    if not targets:
        logger.warning("No chub pins found in .chub/pins.yaml")
        return []

    if namespace_filter is None:
        allowed = None
    elif isinstance(namespace_filter, str):
        allowed = {namespace_filter}
    else:
        allowed = set(namespace_filter)
    docs: list[Document] = []
    successes = 0
    failures = 0

    for target in targets:
        doc_id = target["id"]
        lang = target.get("lang") or "python"
        ns = namespace_for_doc_id(doc_id)
        if allowed is not None and ns not in allowed:
            continue

        logger.info(
            "Fetching chub doc %s (lang=%s, ns=%s, via=%s)",
            doc_id,
            lang,
            ns,
            target.get("source"),
        )
        try:
            markdown = chub_client.get_doc(
                doc_id,
                lang=lang,
                version=target.get("version"),
                match_env=match_env,
            )
            docs.append(
                build_chub_document(
                    markdown,
                    doc_id,
                    language=lang,
                    namespace=ns,
                )
            )
            successes += 1
        except chub_client.ChubError as exc:
            failures += 1
            logger.error("Failed to get %s: %s", doc_id, exc)

    logger.info(
        "Chub load done: %d ok, %d failed, %d documents",
        successes,
        failures,
        len(docs),
    )
    return docs
