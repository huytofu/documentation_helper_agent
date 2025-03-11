from typing import Any, Dict

from agent.graph.chains.generation import generation_chain
from agent.graph.state import GraphState


def generate(state: GraphState) -> Dict[str, Any]:
    print("---GENERATE---")
    query = state["query"]
    documents = state["documents"]
    framework = state.get("framework", "")
    language = state.get("language", "")
    generation = state.get("generation", None)
    comments = state.get("comments", None)
    retry_count = state.get("retry_count", 0)

    joined_documents = "\n\n".join([doc.page_content[:500] for doc in documents[:3]])

    if framework and (framework not in ["none", ""]):
        extra_info = f"and is expert at the {framework} framework"
    else:
        extra_info = ""

    generation = generation_chain.invoke({
        "language": language, "extra_info": extra_info, 
        "documents": joined_documents, "query": query,
        "generation": generation, "comments": comments
    })
    retry_count += 1
    return {"generation": generation, "retry_count": retry_count, "current_node": "GENERATE"}
