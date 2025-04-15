import logging
from typing import Any, Dict
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage
from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.utils.firebase_utils import save_conversation_message_api
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
    if config:
        generating_state = {
            **state,
            "current_node": "INITIALIZE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
    
    # Get and trim messages
    messages = trim_messages(state.get("messages", []))
    # Simplified query and rewritten_query initialization
    if messages:
        # Extract query from last human message
        last_message_type = get_last_message_type(messages)
        if last_message_type == "human":
            query = messages[-1].content
    
    # Extract basic state
    language = state.get("language", "python")
    comments = ""
    framework = ""
    retry_count = 0
    pass_summarize = False
    summarized = False
    documents = []
    
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

    # Save the query as a question in the database if available
    user_id = state.get("user_id", "")
    if query:
        # Set rewritten_query to query if not provided
        result["query"] = query
        result["rewritten_query"] = query
        if user_id:
            try:
                logger.info(f"Saving query as question for user {user_id}")
                await save_conversation_message_api(user_id, "question", query)
                logger.info(f"Successfully saved query for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to save query to database: {e}")
        
    return result