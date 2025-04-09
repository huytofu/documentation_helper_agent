from typing import Any, Dict

from agent.graph.chains.regeneration import regeneration_chain
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from langchain_core.documents import Document
from agent.graph.utils.message_utils import get_page_content
from copilotkit.langgraph import copilotkit_emit_state


async def regenerate(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---REGENERATE---")
    if config:
        generating_state = {
            "current_node": "REGENERATE",
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    rewritten_query = state.get("rewritten_query", "")
    documents = state.get("documents", [])
    framework = state.get("framework", "")
    messages = state.get("messages", [])
    last_message_type = get_last_message_type(messages)
    
    if last_message_type == "human":
        generation = ""
    elif last_message_type == "ai":
        generation = messages[-1].content
    
    comments = state.get("comments", "")

    joined_documents = "\n\n".join([get_page_content(doc) for doc in documents[:3]])

    if framework and (framework not in ["none", ""]):
        extra_info = f"and is expert at the {framework} framework"
    else:
        extra_info = ""

    generation = regeneration_chain.invoke({
        "extra_info": extra_info, 
        "documents": joined_documents, 
        "query": rewritten_query,
        "generation": generation, 
        "comments": comments
    })
    messages.append(AIMessage(content=generation))

    # Return only messages and retry_count
    return {
        "messages": messages
    }
