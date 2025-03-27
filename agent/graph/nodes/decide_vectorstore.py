from typing import Dict, Any
from agent.graph.chains.vectorstore_router import get_vectorstore_route

def decide_vectorstore(state: Dict[str, Any]) -> Dict[str, Any]:
    """Decide which vectorstore to use based on the query."""
    query = state.get("query", "")
    result = get_vectorstore_route(query)
    framework = result.datasource or "none"
    return {"framework": framework, "current_node": "DECIDE_VECTORSTORE"}