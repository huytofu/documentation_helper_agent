from typing import Any, Dict, Optional
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agent.graph.state import GraphState
from agent.graph.retrievers import get_retriever, get_documents_by_doc_id
from agent.graph.chains.retrieval_mode import (
    classify_retrieval_mode,
    encode_retrieval_mode,
)
from agent.graph.stores import (
    CHUB_PACKAGES_NS,
    format_chub_packages_for_prompt,
    get_store,
)
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state, copilotkit_emit_message
from agent.graph.utils.api_utils import standard_sleep

logger = logging.getLogger("graph.nodes.retrieve")


async def _resolve_kb_catalog(
    state: GraphState, runtime: Optional[Runtime] = None
) -> str:
    catalog = (state.get("kb_catalog") or "").strip()
    if catalog:
        return catalog

    items = []
    store = getattr(runtime, "store", None) if runtime is not None else None
    if store is None:
        try:
            store = get_store()
        except Exception:
            logger.exception("retrieve: failed to get store")
            store = None
    if store is not None:
        try:
            search = getattr(store, "asearch", None)
            if callable(search):
                items = await search(CHUB_PACKAGES_NS, limit=200)
            else:
                items = store.search(CHUB_PACKAGES_NS, limit=200)
        except Exception:
            logger.exception("retrieve: chub package catalog read failed")
            items = []
    return format_chub_packages_for_prompt(items)


async def retrieve(
    state: GraphState,
    runtime: Optional[Runtime] = None,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    print("---RETRIEVE---")
    if config:
        generating_state = {
            **state,
            "current_node": "RETRIEVE",
        }
        await copilotkit_emit_state(config, generating_state)
        await copilotkit_emit_message(
            config, "Please wait while I retrieve useful context from knowledge base."
        )
        await standard_sleep()

    query = state.get("query", "")
    vectorstore = state.get("framework", None)
    if vectorstore in [None, "others"]:
        return {
            "documents": [],
            "retrieval_mode": "embedding_match",
            "current_node": "RETRIEVE",
        }

    kb_catalog = await _resolve_kb_catalog(state, runtime)
    decision = classify_retrieval_mode(query, kb_catalog)
    retrieval_mode = encode_retrieval_mode(
        decision, kb_catalog, framework=vectorstore
    )

    if retrieval_mode.startswith("direct_"):
        topic_id = retrieval_mode[len("direct_") :]
        if vectorstore != "chub":
            # Large framework namespaces: refuse via after_retrieve → BROWSE_REFUSE.
            return {
                "documents": [],
                "retrieval_mode": retrieval_mode,
                "kb_catalog": kb_catalog,
                "current_node": "RETRIEVE",
            }
        documents = get_documents_by_doc_id("chub", topic_id)
        return {
            "documents": documents,
            "retrieval_mode": retrieval_mode,
            "kb_catalog": kb_catalog,
            "current_node": "RETRIEVE",
        }

    retriever = get_retriever(vectorstore)
    if retriever is None:
        return {
            "documents": [],
            "retrieval_mode": "embedding_match",
            "kb_catalog": kb_catalog,
            "current_node": "RETRIEVE",
        }
    documents = retriever.invoke(query)
    return {
        "documents": documents,
        "retrieval_mode": "embedding_match",
        "kb_catalog": kb_catalog,
        "current_node": "RETRIEVE",
    }
