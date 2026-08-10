import logging
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agent.graph.state import GraphState
from agent.graph.chains.route_and_framework import get_route_and_framework
from agent.graph.stores import (
    CHUB_PACKAGES_NS,
    format_chub_packages_for_prompt,
)
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import standard_sleep

logger = logging.getLogger("graph.nodes.route_and_framework")


async def route_and_framework(
    state: GraphState,
    runtime: Runtime,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """One LLM call: datasource, programming language, and framework namespace."""
    print("---ROUTE AND FRAMEWORK---")
    if config:
        generating_state = {
            **state,
            "current_node": "ROUTE_AND_FRAMEWORK",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    query = state.get("query", "")
    state_language = state.get("language", "")
    rewritten_query = state.get("rewritten_query", query)

    items = []
    store = getattr(runtime, "store", None)
    if store is not None:
        try:
            items = await store.asearch(CHUB_PACKAGES_NS, limit=200)
        except Exception:
            logger.exception("chub package catalog read failed")
            items = []
    else:
        logger.warning("runtime.store is None; routing without chub package catalog")

    package_block = format_chub_packages_for_prompt(items)
    result = get_route_and_framework(
        query, indexed_chub_packages=package_block
    )

    datasource = result.datasource or "websearch"
    framework = result.framework or "others"
    res_language = result.language or "none"

    # Preserve decide_language side effect when no language is mentioned.
    if res_language in [None, "none"]:
        language = state_language or "python"
        query = f"{query}. Please asnwer in {language} language"
        rewritten_query = (
            f"{rewritten_query}. Please asnwer in {language} language"
            if rewritten_query
            else query
        )
    else:
        language = res_language

    # Only python/javascript use the vectorstore path.
    if datasource == "vectorstore" and language not in ["python", "javascript"]:
        return {
            "datasource": "websearch",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
            "current_node": "ROUTE_AND_FRAMEWORK",
        }

    if datasource == "direct":
        return {
            "datasource": "direct",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
            "current_node": "ROUTE_AND_FRAMEWORK",
        }

    if datasource == "kb_meta":
        return {
            "datasource": "kb_meta",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
            "kb_catalog": package_block or "(none indexed yet)",
            "current_node": "ROUTE_AND_FRAMEWORK",
        }

    if datasource != "vectorstore":
        return {
            "datasource": "websearch",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
            "current_node": "ROUTE_AND_FRAMEWORK",
        }

    return {
        "datasource": "vectorstore",
        "framework": framework,
        "language": language,
        "query": query,
        "rewritten_query": rewritten_query,
        "current_node": "ROUTE_AND_FRAMEWORK",
    }
