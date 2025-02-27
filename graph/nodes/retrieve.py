from typing import Any, Dict
from graph.state import GraphState
from graph.retrievers import get_retriever


def retrieve(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    query = state["query"]
    vectorstore = state["framework"]

    documents = get_retriever(vectorstore).invoke(query)
    return {"documents": documents, "query": query}