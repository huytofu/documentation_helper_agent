from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig

from agent.graph.state import GraphState
from agent.graph.chains.intent_classifier import get_intent
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.api_utils import standard_sleep


async def classify_intent(
    state: GraphState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Classify the query as programming help vs chitchat."""
    print("---CLASSIFY INTENT---")
    if config:
        generating_state = {
            **state,
            "current_node": "CLASSIFY_INTENT",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    query = state.get("query", "")
    result = get_intent(query)
    intent = result.intent or "programming"
    return {"intent": intent, "current_node": "CLASSIFY_INTENT"}
