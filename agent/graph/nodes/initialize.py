import logging
from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from agent.graph.state import GraphState
from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.utils.firebase_utils import save_conversation_message_api
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.message_utils import trim_messages
from agent.graph.utils.api_utils import standard_sleep

logger = logging.getLogger("graph.graph")

async def initialize(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Initialize the graph with the necessary state."""
    print("---INITIALIZE---")
    if config:
        generating_state = {
            **state,
            "current_node": "INITIALIZE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()
    # Get and trim messages (do not re-return messages — add_messages would duplicate)
    messages = trim_messages(state.get("messages", []))
    query = state.get("query", "print: please ask me a question")
    if messages:
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
        "pass_summarize": pass_summarize,
        "summarized": summarized,
        "documents": documents,
        "current_node": "INITIALIZE",
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