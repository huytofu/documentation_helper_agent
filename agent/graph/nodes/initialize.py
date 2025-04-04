import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger("graph.graph")

async def initialize(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Initialize the state with properties from the request."""
    logger.info("---INITIALIZE---")
    if config:
        generating_state = {
            "current_node": "INITIALIZE",
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    messages = state.get("messages", [])
    last_message_type = get_last_message_type(messages)
    
    while last_message_type == "ai":
        messages.pop()
        last_message_type = get_last_message_type(messages)
    
    if last_message_type == "human":
        query = messages[-1].content
    else:
        query = "Tell me about who you are and what you do"
    
    # Create a copy of the state
    state_copy = state.copy()
    
    # Update state with query
    state_copy["query"] = query
    
    # Initialize other required fields if they don't exist
    state_copy["documents"] = []
    state_copy["generation"] = ""
    state_copy["comments"] = ""
    state_copy["retry_count"] = 0
    state_copy["current_node"] = "INITIALIZE"
    
    # Temporarily disabled explicit state emission
    # if config:
    #     output_properties = extract_output_state_properties(state_copy)
    #     await copilotkit_emit_state(config, output_properties)
    
    logger.info(f"Initialized state with query: {query}")
    return {
        "query": state_copy["query"],
        "documents": state_copy["documents"],
        "generation": state_copy["generation"],
        "comments": state_copy["comments"],
        "retry_count": state_copy["retry_count"]
    }