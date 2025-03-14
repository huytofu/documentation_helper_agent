import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type

logger = logging.getLogger("graph.graph")

def initialize(state: GraphState) -> Dict[str, Any]:
    """Initialize the state with properties from the request."""
    logger.info("---INITIALIZE---")
    messages = state["messages"]
    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        query = messages[-1].content
    elif last_message_type == "ai":
        query = ""
    else:
        query = ""
    
    # Create a copy of the state
    state_copy = state.copy()
    
    # Update state with query
    state_copy["query"] = query
    
    # Initialize other required fields if they don't exist
    state_copy["documents"] = []
    state_copy["generation"] = ""
    state_copy["comments"] = ""
    state_copy["retry_count"] = 0
    
    logger.info(f"Initialized state with query: {query}")
    return {
        "query": state_copy["query"],
        "documents": state_copy["documents"],
        "generation": state_copy["generation"],
        "comments": state_copy["comments"],
        "retry_count": state_copy["retry_count"],
        "current_node": "INITIALIZE"
    }