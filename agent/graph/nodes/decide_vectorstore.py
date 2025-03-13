from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.chains.vectorstore_router import vectorstore_router

def decide_vectorstore(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE VECTORSTORE---")
    query = state["query"]
    result = vectorstore_router.invoke({"query": query})
    framework = result.datasource or "none"
    return {"framework": framework, "current_node": "DECIDE_VECTORSTORE"}