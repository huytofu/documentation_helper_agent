"""Chub expert tools, bind_tools model, ToolNode, and document harvest helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
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
# ToolNode has no max-calls param; we trim before invoke and pass max_concurrency.
MAX_CHUB_TOOLS_PER_ROUND = 1

CHUB_EXPERT_SYSTEM = """You are a documentation enricher for a RAG agent.
Pinecone retrieval returned nothing useful. Use chub tools to find curated library docs.

STOP RULES (critical — gpt-oss multi-channel models):
- You are given multiple rounds to use tools and observe their results so select exactly 1 tool each round only.
- After emitting that one tool call, STOP immediately. Do not continue generating.
- Do NOT invent tool results, Output/Observation, or "Now we have…" text in the same turn.
- Do NOT call a second tool (e.g. ingest_doc) in the same turn as get_doc or search_docs.
- Do NOT write a final summary in the same turn as any tool call. Final text only when you make zero tool calls.
- Wait for the real ToolMessage in the next round before deciding the next action.

Rules:
- Prefer search_docs then get_doc (at most 2–4 docs), one call per round.
- Use list_pins when the topic matches the pinned expert corpus.
- get_doc doc_id MUST be taken strictly from the results list returned by search_docs (or from list_pins). Never invent, guess, or rewrite ids. Pick the id that matches the user's query the most.
- get_doc saves a file and returns only {doc_id, name, path} — never document body.
- Every successful get_doc MUST be followed by an ingest_doc attempt with the returned path (next round only, after you see the get_doc ToolMessage).
- If get_doc returns an error, do not call ingest_doc for that id. Next round: call get_doc again with a correct id from the prior search_docs results (if any remain).
- Do not invent doc_ids or paths. Only use values returned by tools.
- Never request or echo document bodies.
- When finished (all desired docs ingested, or no valid ids left), reply with a short plain-text summary of saved names/paths (no more tool calls).

SCENARIOS:

A)
STEP 1:
Called search_docs. Argument: query="stripe payments"
search_docs(query="stripe payments", limit=3)
Output/Observation:
{
  "query": "stripe payments",
  "results": [],
  "showing": 0,
  "total": 0
}
Conclusion: No results. Stop. Do not call get_doc or ingest_doc.

B)
STEP 1:
Called search_docs. Argument: query="stripe payments"
search_docs(query="stripe payments")
Output/Observation:
{
  "query": "stripe payments",
  "results": ["stripe/api", "stripe/payments"],
  "showing": 2,
  "total": 2
}
Conclusion: Next round call get_doc for the first result only (one tool per round). Use only ids from this results list.

STEP 2:
Called get_doc. Argument: doc_id="stripe/api"
get_doc(doc_id="stripe/api")
Output/Observation:
{
  "doc_id": "stripe/api",
  "name": "stripe/api",
  "path": ".chub/fetched/stripe/api.md"
}
Conclusion: File saved. Next round must call ingest_doc only.

STEP 3:
Called ingest_doc. Argument: path=".chub/fetched/stripe/api.md"
ingest_doc(path=".chub/fetched/stripe/api.md")
Output/Observation:
{
  "success": true,
  "doc_id": "stripe/api",
  "namespace": "chub",
  "title": "stripe/api",
  "path": ".chub/fetched/stripe/api.md"
}
Conclusion: Ingested. Later rounds: get_doc then ingest_doc for "stripe/payments" (still one tool per round), then stop with a short path summary.

C)
STEP 1:
Called search_docs. Argument: query="binance trading"
search_docs(query="binance trading")
Output/Observation:
{
  "query": "binance trading",
  "results": ["binance/trading"],
  "showing": 1,
  "total": 1
}
Conclusion: Only "binance/trading" is valid. Do not invent ids like "binance/sdk" or "binance/api".

STEP 2 (WRONG — invented id):
Called get_doc. Argument: doc_id="binance/sdk"
get_doc(doc_id="binance/sdk")
Output/Observation:
{
  "error": "chub get binance/sdk -o /app/.chub/fetched/binance/sdk.md --lang python failed (exit 1): \\u001b[31mError: No doc or skill found with id \\"binance/sdk\\".\\u001b[39m"
}
Conclusion: get_doc failed. Do NOT call ingest_doc. Next round call get_doc with the correct id from search results: "binance/trading".

STEP 3 (recovery):
Called get_doc. Argument: doc_id="binance/trading"
get_doc(doc_id="binance/trading")
Output/Observation:
{
  "doc_id": "binance/trading",
  "name": "binance/trading",
  "path": ".chub/fetched/binance/trading.md"
}
Conclusion: Success. Next round call ingest_doc with that path only.
"""


def limit_ai_message_tool_calls(
    message: AIMessage, max_calls: int = MAX_CHUB_TOOLS_PER_ROUND
) -> AIMessage:
    """Keep only the first N tool_calls so at most N reach ToolNode."""
    tool_calls = list(message.tool_calls or [])
    if len(tool_calls) <= max_calls:
        return message

    kept = tool_calls[:max_calls]
    kept_ids = {call.get("id") for call in kept if call.get("id")}
    additional_kwargs = dict(message.additional_kwargs or {})
    raw = additional_kwargs.get("tool_calls")
    if isinstance(raw, list) and kept_ids:
        filtered = []
        for item in raw:
            call_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            if call_id in kept_ids:
                filtered.append(item)
        if filtered:
            additional_kwargs["tool_calls"] = filtered
        else:
            additional_kwargs.pop("tool_calls", None)

    return AIMessage(
        content=message.content,
        tool_calls=kept,
        id=message.id,
        name=message.name,
        additional_kwargs=additional_kwargs,
        response_metadata=dict(getattr(message, "response_metadata", None) or {}),
        invalid_tool_calls=list(getattr(message, "invalid_tool_calls", None) or []),
    )


def prepare_chub_ai_message(
    message: AIMessage, max_calls: int = MAX_CHUB_TOOLS_PER_ROUND
) -> AIMessage:
    """Trim tool_calls and clear content when tools are present.

    gpt-oss often appends fake observations / ingest / final in the same
    completion as the first tool call; storing that content poisons the next round.
    """
    if not message.tool_calls:
        return message

    limited = limit_ai_message_tool_calls(message, max_calls)
    content = limited.content
    has_content = bool(content) if not isinstance(content, str) else bool(content.strip())
    if limited is message and not has_content:
        return message

    return AIMessage(
        content="",
        tool_calls=list(limited.tool_calls or []),
        id=limited.id,
        name=limited.name,
        additional_kwargs=dict(limited.additional_kwargs or {}),
        response_metadata=dict(getattr(limited, "response_metadata", None) or {}),
        invalid_tool_calls=list(getattr(limited, "invalid_tool_calls", None) or []),
    )


def _get_doc_success_payload(doc_id: str) -> dict[str, str]:
    return {
        "doc_id": doc_id,
        "name": doc_id,
        "path": chub_client.rel_fetched_path(doc_id),
    }


def _resolve_under_fetched(path: str) -> Path:
    """Resolve path to an absolute file under `.chub/fetched/`; raise ValueError otherwise."""
    root = chub_client.PROJECT_ROOT.resolve()
    fetched_root = (root / ".chub" / "fetched").resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (root / path).resolve()
    else:
        candidate = candidate.resolve()
    try:
        candidate.relative_to(fetched_root)
    except ValueError as exc:
        raise ValueError(f"path must be under .chub/fetched/: {path}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"fetched file not found: {path}")
    return candidate


def _doc_id_from_fetched_file(path: Path, markdown: str) -> str:
    frontmatter, _ = chub_client.parse_frontmatter(markdown)
    name = frontmatter.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    fetched_root = (chub_client.PROJECT_ROOT / ".chub" / "fetched").resolve()
    rel = path.resolve().relative_to(fetched_root).as_posix()
    if rel.endswith(".md"):
        rel = rel[: -len(".md")]
    return rel


def _project_rel_posix(path: Path) -> str:
    return path.resolve().relative_to(chub_client.PROJECT_ROOT.resolve()).as_posix()


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
    """Fetch a chub doc to `.chub/fetched/` and return {doc_id, name, path} only (no body)."""
    try:
        abs_path = chub_client.fetched_path_for_doc_id(doc_id)
        if not abs_path.is_file():
            chub_client.get_doc_to_file(
                doc_id,
                abs_path,
                lang=lang,
                version=version,
                match_env=match_env,
            )
        return json.dumps(_get_doc_success_payload(doc_id), indent=2)
    except ChubError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_doc failed")
        return json.dumps({"error": str(exc)})


@tool
def ingest_doc(
    path: str,
    namespace: Optional[str] = None,
) -> str:
    """Ingest a previously saved chub markdown file from `.chub/fetched/` into Pinecone."""
    try:
        from ingestion.documents import build_chub_document, ingest_documents

        abs_path = _resolve_under_fetched(path)
        markdown = abs_path.read_text(encoding="utf-8")
        doc_id = _doc_id_from_fetched_file(abs_path, markdown)
        ns = namespace or namespace_for_doc_id(doc_id)
        doc = build_chub_document(markdown, doc_id, namespace=ns)
        ok = ingest_documents(ns, [doc])
        return json.dumps(
            {
                "success": ok,
                "doc_id": doc_id,
                "namespace": ns,
                "title": doc.metadata.get("title"),
                "path": _project_rel_posix(abs_path),
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

# b) ToolNode runs tool_calls from the last AIMessage.
# ToolNode has no max-calls setting; chub_tools trims to MAX_CHUB_TOOLS_PER_ROUND
# and invokes with max_concurrency=MAX_CHUB_TOOLS_PER_ROUND.
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
    """Build Documents by reading files listed in get_doc / ingest_doc ToolMessages."""
    from ingestion.documents import build_chub_document

    name_by_id = _tool_name_by_call_id(chub_messages)
    documents: List[Document] = []
    seen_paths: set[str] = set()

    for message in chub_messages:
        if not isinstance(message, ToolMessage):
            continue
        tool_name = name_by_id.get(message.tool_call_id) or getattr(
            message, "name", None
        )
        if tool_name not in ("get_doc", "ingest_doc"):
            continue
        content = (
            message.content if isinstance(message.content, str) else str(message.content)
        )
        if not content:
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("error"):
            continue
        rel_path = payload.get("path")
        if not isinstance(rel_path, str) or not rel_path or rel_path in seen_paths:
            continue
        seen_paths.add(rel_path)
        abs_path = (chub_client.PROJECT_ROOT / rel_path).resolve()
        if not abs_path.is_file():
            logger.warning("harvest skip missing file: %s", rel_path)
            continue
        try:
            markdown = abs_path.read_text(encoding="utf-8")
        except OSError:
            logger.exception("harvest failed reading %s", rel_path)
            continue
        doc_id = payload.get("doc_id") or _doc_id_from_fetched_file(abs_path, markdown)
        doc = build_chub_document(markdown, str(doc_id))
        documents.append(doc)

    return documents
