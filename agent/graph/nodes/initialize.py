import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage
from agent.graph.utils.message_utils import get_last_message_type

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
    comments = state.get("comments", "")
    framework = state.get("framework", "")
    retry_count = state.get("retry_count", 0)
    
    # Simplified query and rewritten_query initialization
    query = state.get("query", "")
    if not query and messages:
        # Extract query from last human message
        last_message_type = get_last_message_type(messages)
        if last_message_type == "human":
            query = messages[-1].content
    # Set rewritten_query to query if not provided
    rewritten_query = state.get("rewritten_query", query)

    pass_summarize = state.get("pass_summarize", False)
    summarized = state.get("summarized", False)
    documents = state.get("documents", [])
    
    # Build result
    result = {
        "language": language,
        "comments": comments,
        "framework": framework,
        "retry_count": retry_count,
        "messages": messages,
        "pass_summarize": pass_summarize,
        "summarized": summarized,
        "documents": documents,
    }
    
    if query:
        result["query"] = query
        result["rewritten_query"] = rewritten_query
        
    return result