from typing import Any, Dict

from graph.chains.generation import generation_chain
from graph.state import GraphState


def generate(state: GraphState) -> Dict[str, Any]:
    print("---GENERATE---")
    query = state["query"]
    documents = state["documents"]
    framework = state["framework"]
    language = state["language"]
    generation = state.get("generation", None)
    comment = state.get("comment", None)
    retry_count = state.get("retry_count", 0)

    joined_documents = "\n\n".join([doc.page_content for doc in documents])

    generation = generation_chain.invoke({
        "language": language,"framework": framework, 
        "documents": joined_documents, "query": query,
        "generation": generation, "comment": comment
    })
    retry_count += 1
    return {"generation": generation, "retry_count": retry_count}
