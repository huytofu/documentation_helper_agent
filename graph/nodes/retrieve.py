from typing import Any, Dict
from graph.state import GraphState
from graph.retrievers import get_retriever


def retrieve(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    query = state["query"]
    vectorstore = state["framework"]
    language = state["language"]
    retriever = get_retriever(vectorstore, language)
    if retriever is None:
        return {"documents": [], "query": query}
    else:
        documents = retriever.invoke(query)
        return {"documents": documents, "query": query}