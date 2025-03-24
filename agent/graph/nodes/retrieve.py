from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.retrievers import get_retriever


def retrieve(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    query = state["query"]
    vectorstore = state["framework"]
    if vectorstore is None:
        return {"documents": [], "current_node": "RETRIEVE"}
    retriever = get_retriever(vectorstore)
    if retriever is None:
        return {"documents": [], "current_node": "RETRIEVE"}
    else:
        documents = retriever.invoke(query)
        return {"documents": documents, "current_node": "RETRIEVE"}