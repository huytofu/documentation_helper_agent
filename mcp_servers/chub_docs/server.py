"""MCP server: search / get / ingest curated chub docs into Pinecone."""

from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ingestion import chub_client
from ingestion.namespace_map import namespace_for_doc_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_servers.chub_docs")

mcp = FastMCP(
    "chub-docs",
    instructions=(
        "Search and fetch curated library docs via chub for packages the user is "
        "asking about, and optionally ingest them into Pinecone. Baseline expert "
        "corpus for agentic development lives in .chub/pins.yaml (list_pins)."
    ),
)


@mcp.tool()
def search_docs(
    query: str,
    lang: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search the chub registry for docs about a package the user is asking about.

    Use when Pinecone has no/insufficient coverage for the user's question
    (not for this agent's own dependencies).

    Args:
        query: Package or topic the user is exploring (e.g. "stripe payments").
        lang: Optional language filter (python, javascript, ...).
        tags: Optional comma-separated tags.
        limit: Max results (default 20).
    """
    data = chub_client.search(query, lang=lang, tags=tags, type_="doc", limit=limit)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_doc(
    doc_id: str,
    lang: Optional[str] = "python",
    version: Optional[str] = None,
    match_env: bool = False,
) -> str:
    """Fetch a chub documentation entry as markdown.

    Args:
        doc_id: Entry id such as openai/chat or langgraph/package.
        lang: Language variant (default python).
        version: Optional explicit version.
        match_env: If true, try to match installed dependency versions first.
    """
    content = chub_client.get_doc(
        doc_id, lang=lang, version=version, match_env=match_env
    )
    return content


@mcp.tool()
def ingest_doc(
    doc_id: str,
    lang: Optional[str] = "python",
    version: Optional[str] = None,
    match_env: bool = False,
    namespace: Optional[str] = None,
) -> str:
    """Fetch a chub doc, chunk it, and add it to the Pinecone namespace.

    Namespace is inferred from doc_id unless overridden
    (langgraph/* → langgraph, copilotkit/* → copilotkit, else chub).

    Args:
        doc_id: Entry id to ingest.
        lang: Language variant (default python).
        version: Optional explicit version.
        match_env: Prefer installed dependency versions when possible.
        namespace: Optional Pinecone namespace override.
    """
    from ingestion.documents import build_chub_document, ingest_documents

    markdown = chub_client.get_doc(
        doc_id, lang=lang, version=version, match_env=match_env
    )
    ns = namespace or namespace_for_doc_id(doc_id)
    doc = build_chub_document(markdown, doc_id, language=lang, namespace=ns)
    ok = ingest_documents(ns, [doc])
    payload = {
        "success": ok,
        "doc_id": doc_id,
        "namespace": ns,
        "language": lang,
        "title": doc.metadata.get("title"),
        "version": doc.metadata.get("version"),
    }
    return json.dumps(payload, indent=2)


@mcp.tool()
def list_pins() -> str:
    """List the curated expert corpus pinned in .chub/pins.yaml (agentic-dev baseline)."""
    pins = chub_client.list_pins()
    if not pins:
        pins = chub_client.read_pins_yaml()
    return json.dumps({"pins": pins, "total": len(pins)}, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
