from typing import Any, Dict

from agent.graph.chains.generation import generation_chain
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from langchain_core.documents import Document
from agent.graph.utils.message_utils import get_page_content
from copilotkit.langgraph import copilotkit_emit_state


async def generate(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---GENERATE---")
    query = state["query"]
    documents = state["documents"]
    framework = state.get("framework", "")
    language = state.get("language", "")
    messages = state["messages"]
    last_message_type = get_last_message_type(messages)
    
    if last_message_type == "human":
        generation = ""
    elif last_message_type == "ai":
        generation = messages[-1].content
    
    comments = state.get("comments", None)
    retry_count = state.get("retry_count", 0)

    # Create result state with current_node
    result_state = {
        "messages": messages, 
        "retry_count": retry_count, 
        "current_node": "GENERATE"
    }

    # Emit state update with only OutputGraphState properties
    if config:
        output_properties = extract_output_state_properties(result_state)
        await copilotkit_emit_state(config, output_properties)

    joined_documents = "\n\n".join([get_page_content(doc) for doc in documents[:3]])

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
    
    return result_state
