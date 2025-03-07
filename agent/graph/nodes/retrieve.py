from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.retrievers import get_retriever


def retrieve(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    query = state["query"]
    vectorstore = state["framework"]
    language = state["language"]
    if vectorstore is None:
        return {"documents": []}
    retriever = get_retriever(vectorstore, language)
    if retriever is None:
        return {"documents": []}
    else:
        documents = retriever.invoke(query)
        return {"documents": documents}