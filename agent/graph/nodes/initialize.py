import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger("graph.graph")

def trim_messages(messages: list, max_messages: int = 8) -> list:
    """Trim the messages list to contain only the last N messages."""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

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
    
    # Trim messages to last 8
    messages = trim_messages(messages)
    
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
    
    # Update state with query and trimmed messages
    state_copy["query"] = query
    state_copy["rewritten_query"] = ""
    state_copy["pass_summarize"] = False
    state_copy["summarized"] = False
    state_copy["messages"] = messages
    
    # Initialize other required fields if they don't exist
    state_copy["documents"] = []
    state_copy["generation"] = ""
    state_copy["comments"] = ""
    state_copy["retry_count"] = 0
    
    # Temporarily disabled explicit state emission
    # if config:
    #     output_properties = extract_output_state_properties(state_copy)
    #     await copilotkit_emit_state(config, output_properties)
    
    logger.info(f"Initialized state with query: {query}")
    return {
        "query": state_copy["query"],
        "messages": state_copy["messages"],
        "documents": state_copy["documents"],
        "generation": state_copy["generation"],
        "comments": state_copy["comments"],
        "retry_count": state_copy["retry_count"]
    }