from typing import Any, Dict

from agent.graph.chains.generation import generation_chain
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage


def generate(state: GraphState) -> Dict[str, Any]:
    print("---GENERATE---")
    query = state["query"]
    documents = state["documents"]
    framework = state.get("framework", "")
    language = state.get("language", "")
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.type == "human" or isinstance(last_message, HumanMessage):
        generation = ""
    elif last_message.type == "ai" or isinstance(last_message, AIMessage):
        generation = last_message.get("content", "")
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
    messages.append(AIMessage(content=generation))
    retry_count += 1
    return {"messages": messages, "retry_count": retry_count, "current_node": "GENERATE"}
