import logging
from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage
from agent.graph.state import GraphState
from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.utils.firebase_utils import save_conversation_message_api
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.message_utils import (
    messages_to_strip_for_next_run,
    sanitize_messages_for_next_run,
)
from agent.graph.utils.api_utils import standard_sleep

logger = logging.getLogger("graph.graph")

async def initialize(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Initialize the graph with the necessary state."""
    print("---INITIALIZE---")

    raw_messages = list(state.get("messages", []))
    # Drop AG-UI-merged tool/status/stream-dupe messages; keep durable chat turns.
    durable_messages = sanitize_messages_for_next_run(raw_messages)
    strip_messages = messages_to_strip_for_next_run(raw_messages)
    message_removals = [
        RemoveMessage(id=m.id) for m in strip_messages if getattr(m, "id", None)
    ]

    query = state.get("query", "print: please ask me a question")
    if durable_messages:
        last_message_type = get_last_message_type(durable_messages)
        if last_message_type == "human":
            query = durable_messages[-1].content

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
        # Clear prior-turn chub enrich transcript / flags.
        "chub_messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
        "chub_enrich_attempted": False,
        "chub_tool_rounds": 0,
        "chub_consent": False,
        "pending_question": None,
        # Persist message cleanup via add_messages RemoveMessage updates.
        "messages": message_removals,
    }

    if config:
        generating_state = {
            **state,
            **result,
            "messages": durable_messages,
            "chub_messages": [],
            "query": query if query else state.get("query", ""),
            "rewritten_query": query if query else state.get("query", ""),
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

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
