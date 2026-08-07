"""Chub expert tools, bind_tools model, ToolNode, and document harvest helpers."""

from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from agent.graph.models.chub_expert import llm
from ingestion import chub_client
from ingestion.chub_client import ChubError
from ingestion.namespace_map import namespace_for_doc_id

logger = logging.getLogger("graph.chains.chub_expert")

MAX_CHUB_TOOL_ROUNDS = 6

CHUB_EXPERT_SYSTEM = """You are a documentation enricher for a RAG agent.
Pinecone retrieval returned nothing useful. Use chub tools to find curated library docs.

Rules:
- Prefer search_docs then get_doc (at most 1–3 docs).
- Use list_pins when the topic matches the pinned expert corpus.
- Call ingest_doc only when a fetched doc is clearly worth caching for later sessions.
- Stop when you have enough markdown to answer, or when search/get returns nothing useful.
- Do not invent doc_ids. Only use ids returned by tools.
- When finished, reply with a short plain-text summary of what you fetched (no more tool calls).
"""


@tool
def search_docs(
    query: str,
    lang: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search the chub registry for docs about a package the user is asking about."""
    try:
        data = chub_client.search(
            query, lang=lang, tags=tags, type_="doc", limit=limit
        )
        return json.dumps(data, indent=2)
    except ChubError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001 — surface to the LLM as tool output
        logger.exception("search_docs failed")
        return json.dumps({"error": str(exc)})


@tool
def get_doc(
    doc_id: str,
    lang: Optional[str] = "python",
    version: Optional[str] = None,
    match_env: bool = False,
) -> str:
    """Fetch a chub documentation entry as markdown."""
    try:
        return chub_client.get_doc(
            doc_id, lang=lang, version=version, match_env=match_env
        )
    except ChubError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_doc failed")
        return json.dumps({"error": str(exc)})


@tool
def ingest_doc(
    doc_id: str,
    lang: Optional[str] = "python",
    version: Optional[str] = None,
    match_env: bool = False,
    namespace: Optional[str] = None,
) -> str:
    """Fetch a chub doc, chunk it, and add it to the Pinecone namespace."""
    try:
        from ingestion.documents import build_chub_document, ingest_documents

        markdown = chub_client.get_doc(
            doc_id, lang=lang, version=version, match_env=match_env
        )
        ns = namespace or namespace_for_doc_id(doc_id)
        doc = build_chub_document(markdown, doc_id, language=lang, namespace=ns)
        ok = ingest_documents(ns, [doc])
        return json.dumps(
            {
                "success": ok,
                "doc_id": doc_id,
                "namespace": ns,
                "title": doc.metadata.get("title"),
                "markdown_preview": markdown[:2000],
            },
            indent=2,
        )
    except ChubError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_doc failed")
        return json.dumps({"error": str(exc)})


@tool
def list_pins() -> str:
    """List the curated expert corpus pinned in .chub/pins.yaml."""
    try:
        pins = chub_client.list_pins() or chub_client.read_pins_yaml()
        return json.dumps({"pins": pins, "total": len(pins)}, indent=2)
    except ChubError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_pins failed")
        return json.dumps({"error": str(exc)})


CHUB_TOOLS = [list_pins, search_docs, get_doc, ingest_doc]

# a) Attach tool schemas so the model can emit structured tool_calls
llm_with_tools = llm.bind_tools(CHUB_TOOLS)

# b) ToolNode runs tool_calls from the last AIMessage (incl. parallel calls)
chub_tool_node = ToolNode(
    CHUB_TOOLS,
    messages_key="chub_messages",
    handle_tool_errors=True,
)


def _tool_name_by_call_id(messages: List[BaseMessage]) -> dict[str, str]:
    names: dict[str, str] = {}
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls or []:
            call_id = call.get("id")
            name = call.get("name")
            if call_id and name:
                names[call_id] = name
    return names


def harvest_chub_documents(chub_messages: List[Any]) -> List[Document]:
    """Build Documents from successful get_doc / ingest_doc ToolMessages."""
    name_by_id = _tool_name_by_call_id(chub_messages)
    documents: List[Document] = []
    seen_fingerprints: set[str] = set()

    for message in chub_messages:
        if not isinstance(message, ToolMessage):
            continue
        tool_name = name_by_id.get(message.tool_call_id) or getattr(
            message, "name", None
        )
        content = message.content if isinstance(message.content, str) else str(message.content)
        if not content or content.strip().startswith('{"error"'):
            continue

        if tool_name == "get_doc":
            fingerprint = content[:200]
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            documents.append(
                Document(
                    page_content=content,
                    metadata={"source": "chub", "tool": "get_doc"},
                )
            )
        elif tool_name == "ingest_doc":
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue
            if payload.get("error"):
                continue
            preview = payload.get("markdown_preview") or ""
            if not preview:
                continue
            fingerprint = preview[:200]
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            documents.append(
                Document(
                    page_content=preview,
                    metadata={
                        "source": "chub",
                        "tool": "ingest_doc",
                        "doc_id": payload.get("doc_id"),
                        "namespace": payload.get("namespace"),
                        "title": payload.get("title"),
                    },
                )
            )

    return documents
