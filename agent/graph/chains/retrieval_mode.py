"""Classify whether RETRIEVE should dump a catalog topic or embedding-match."""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agent.graph.models.retrieval_mode import llm

logger = logging.getLogger(__name__)


class RetrievalModeDecision(BaseModel):
    """Browse dump vs normal similarity search."""

    mode: Literal["embedding_match", "direct"] = Field(
        ...,
        description=(
            "direct when the user wants to read/browse/dump a specific indexed "
            "chub catalog topic; embedding_match for normal Q&A retrieval"
        ),
    )
    topic_id: str = Field(
        default="",
        description="Exact catalog doc_id when mode is direct; otherwise empty",
    )


parser = PydanticOutputParser(pydantic_object=RetrievalModeDecision)

system = """You decide how the documentation retriever should fetch context.

You must set "mode" to exactly one of:
- "direct": ONLY when the user wants to read, show, browse, or dump the full contents of a specific indexed topic
- "embedding_match": how-to / API / explain questions, or any query that is not clearly browsing one topic

When mode is "direct", set "topic_id" to either:
- an exact chub catalog doc_id (e.g. stripe/package), OR
- a framework namespace name when the user wants to dump that whole corpus: langgraph, copilotkit, or chub
Never invent other ids.
When mode is "embedding_match", set "topic_id" to "".

If the user is asking how to use a library (not dump its docs), use embedding_match even if a package name appears.
If neither a catalog doc_id nor a known framework namespace is clearly requested for browsing, use embedding_match.

Indexed chub packages catalog:
{indexed_chub_packages}

VERY IMPORTANT: Answer in JSON only:

{{
    "mode": "embedding_match" or "direct",
    "topic_id": "exact-doc-id-or-framework-or-empty"
}}

DO NOT RETURN ANY OTHER TEXT AFTER THE JSON.
"""

retrieval_mode_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

retrieval_mode_classifier = retrieval_mode_prompt | llm | parser


def parse_catalog_doc_ids(catalog: str) -> set[str]:
    """Extract doc_ids from format_chub_packages_for_prompt output."""
    if not catalog or not catalog.strip() or catalog.strip() == "(none indexed yet)":
        return set()
    ids: set[str] = set()
    for line in catalog.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        rest = line[2:].strip()
        if not rest:
            continue
        doc_id = rest.split(" (", 1)[0].strip()
        if doc_id:
            ids.add(doc_id)
    return ids


def encode_retrieval_mode(
    decision: RetrievalModeDecision,
    catalog: str,
    framework: str | None = None,
) -> str:
    """Map classifier output to state retrieval_mode string.

    Allows topic_id from the chub catalog, or the already-routed framework
    namespace (so large-namespace browse can hit BROWSE_REFUSE).
    """
    if decision is None or decision.mode != "direct":
        return "embedding_match"
    topic_id = (decision.topic_id or "").strip()
    if not topic_id:
        return "embedding_match"
    if topic_id in parse_catalog_doc_ids(catalog):
        return f"direct_{topic_id}"
    fw = (framework or "").strip()
    if fw and topic_id == fw and fw not in ("", "others", "none"):
        return f"direct_{topic_id}"
    return "embedding_match"


def classify_retrieval_mode(
    query: str, indexed_chub_packages: str = "(none indexed yet)"
) -> RetrievalModeDecision:
    """Invoke the retrieval-mode classifier; fail safe to embedding_match."""
    try:
        return retrieval_mode_classifier.invoke(
            {
                "query": query,
                "indexed_chub_packages": indexed_chub_packages
                or "(none indexed yet)",
            }
        )
    except Exception:
        logger.exception("retrieval_mode classifier failed; defaulting to embedding_match")
        return RetrievalModeDecision(mode="embedding_match", topic_id="")
