import logging
from agent.graph.state import GraphState

logger = logging.getLogger("graph.graph")

def initialize(state: GraphState) -> GraphState:
    """Initialize the state with properties from the request."""
    logger.info("---INITIALIZING STATE---")
    
    # Create a copy of the state
    state_copy = state.copy()
    
    # Get the last message from the state
    last_message = state_copy["messages"][-1]
    query = last_message["content"]
    
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
    return state_copy 