from typing import Any, Dict

from agent.graph.state import GraphState
from agent.graph.chains.route_and_framework import get_route_and_framework
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import standard_sleep


async def route_and_framework(
    state: GraphState, config: Dict[str, Any] = None
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
    result = get_route_and_framework(query)

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
        }

    if datasource == "direct":
        return {
            "datasource": "direct",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
        }

    if datasource != "vectorstore":
        return {
            "datasource": "websearch",
            "framework": "others",
            "language": language,
            "query": query,
            "rewritten_query": rewritten_query,
        }

    return {
        "datasource": "vectorstore",
        "framework": framework,
        "language": language,
        "query": query,
        "rewritten_query": rewritten_query,
    }
