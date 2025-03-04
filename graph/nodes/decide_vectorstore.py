from typing import Any, Dict
from graph.state import GraphState
from graph.chains.vectorstore_router import vectorstore_router

def decide_vectorstore(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE VECTORSTORE---")
    query = state["query"]
    vectorstore = vectorstore_router.invoke({"query": query})
    return {"framework": vectorstore}