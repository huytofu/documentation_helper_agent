from typing import Any, Dict

from copilotkit.langgraph import copilotkit_emit_state

from agent.graph.chains.route_and_framework import get_route_and_framework
from agent.graph.state import GraphState
from agent.graph.utils.api_utils import standard_sleep


async def route_and_framework(
    state: GraphState, config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """One LLM call: choose websearch vs vectorstore and the framework namespace."""
    print("---ROUTE AND FRAMEWORK---")
    if config:
        generating_state = {
            **state,
            "current_node": "ROUTE_AND_FRAMEWORK",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    query = state.get("query", "")
    language = state.get("language", "")
    result = get_route_and_framework(query)

    datasource = result.datasource or "websearch"
    framework = result.framework or "others"

    # Preserve prior language gate: only python/javascript use the vectorstore path.
    if datasource == "vectorstore" and language not in ["python", "javascript"]:
        return {"datasource": "websearch", "framework": "others"}

    if datasource != "vectorstore":
        return {"datasource": "websearch", "framework": "others"}

    return {"datasource": "vectorstore", "framework": framework}
