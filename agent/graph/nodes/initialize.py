import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("graph.graph")

def initialize(state: GraphState) -> Dict[str, Any]:
    """Initialize the state with properties from the request."""
    logger.info("---INITIALIZING STATE---")
    
    # Create a copy of the state
    state_copy = state.copy()
    
    # Get the last message from the state
    last_message = state_copy["messages"][-1]
    
    # Handle different message types
    if isinstance(last_message, HumanMessage):
        query = last_message.content
    elif isinstance(last_message, AIMessage):
        query = last_message.content
    else:
        # If it's a dict, try to get content
        query = last_message.get("content", "")
    
    # Update state with query
    state_copy["query"] = query
    
    # Initialize other required fields if they don't exist
    if "documents" not in state_copy:
        state_copy["documents"] = []
    if "generation" not in state_copy:
        state_copy["generation"] = ""
    if "comments" not in state_copy:
        state_copy["comments"] = ""
    if "retry_count" not in state_copy:
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