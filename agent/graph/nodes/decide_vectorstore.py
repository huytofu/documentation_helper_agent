from typing import Dict, Any
from agent.graph.chains.vectorstore_router import get_vectorstore_route
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.state import GraphState

async def decide_vectorstore(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Decide which vectorstore to use based on the query."""
    print("---DECIDE VECTORSTORE---")
    if config:
        generating_state = {
            **state,
            "current_node": "DECIDE_VECTORSTORE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    
    
    query = state.get("query", "")
    result = get_vectorstore_route(query)
    framework = result.datasource or "none"
    
    return {"framework": framework}