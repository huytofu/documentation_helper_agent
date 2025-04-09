import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage
from agent.graph.utils.message_utils import get_last_message_type
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger("graph.graph")

def trim_messages(messages: list, max_messages: int = 8) -> list:
    """Trim the messages list to contain only the last N messages."""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

async def initialize(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Initialize the graph with the necessary state."""
    print("---INITIALIZE---")
    
    # Get and trim messages
    messages = trim_messages(state.get("messages", []))
    
    # Extract basic state
    language = state.get("language", "python")
    documents = state.get("documents", [])
    
    # Simplified query and rewritten_query initialization
    query = state.get("query", "")
    if not query and messages:
        # Extract query from last human message
        last_message_type = get_last_message_type(messages)
        if last_message_type == "human":
            query = messages[-1].content
    
    # Set rewritten_query to query if not provided
    rewritten_query = state.get("rewritten_query", query)
    
    # Emit state if config is provided
    if config:
        await copilotkit_emit_state(config, {
            "language": language,
            "current_node": "INITIALIZE",
            "rewritten_query": rewritten_query,
            "query": query,
            "retry_count": state.get("retry_count", 0),
            "framework": state.get("framework", ""),
            "messages": messages
        })
    
    # Build result
    result = {
        "language": language,
        "documents": documents,
        "current_node": "INITIALIZE",
        "messages": messages
    }
    
    if query:
        result["query"] = query
        result["rewritten_query"] = rewritten_query
        
    return result