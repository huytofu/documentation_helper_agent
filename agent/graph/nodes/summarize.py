from typing import Any, Dict
import asyncio
from agent.graph.state import GraphState
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import (
    cost_tracker,
)
from agent.graph.utils.message_utils import trim_messages
from agent.graph.utils.api_utils import standard_sleep
from agent.graph.chains.summary import invoke_summary_chain

import logging
logger = logging.getLogger(__name__)

# Define timeout for summarization (30 seconds as requested)
SUMMARIZE_TIMEOUT = 30

def simplify_messages(messages: list) -> list:
    """Simplify messages to only include human messages and assistant messages."""
    simplified_messages = []
    for message in messages:
        if message.type == "human":
            simplified_messages.append({"role": "user", "content": message.content})
        elif message.type in ["assistant", "ai"]:
            simplified_messages.append({"role": "assistant", "content": message.content})
    return simplified_messages

async def summarize(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---SUMMARIZE---")
    # Emit state update for summarization
    query = state.get("query", "")
    if "Please write code in" in query:
        desired_language = query.split("Please write code in")[-1]
        instructions = f"Please write code in {desired_language}"
    else:
        instructions = ""

    if config:
        summarizing_state = {
            **state,
            "current_node": "SUMMARIZE"
        }
        # print(f"Emitting summarizing state: {summarizing_state}")
        await copilotkit_emit_state(config, summarizing_state)
        await standard_sleep()
    messages = state.get("messages", [])
    messages = trim_messages(messages)
    messages = simplify_messages(messages)

    try:
        # Use asyncio to handle concurrent summarization requests with timeout
        summary_result = await asyncio.wait_for(
            asyncio.to_thread(
                invoke_summary_chain,
                messages,
                instructions
            ),
            timeout=SUMMARIZE_TIMEOUT
        )
        
        # Track API usage
        if summary_result is not None:
            try:
                result_text = summary_result.rewritten_query
            except Exception as e:
                result_text = summary_result["rewritten_query"]
        else:
            result_text = ""

        cost_tracker.track_usage(
            'summarizer',
            tokens=len(result_text.split()),  # Approximate token count
            cost=0.0,  # Update cost based on actual pricing
            requests=1
        )

        # Update the query in state with the summarized result
        rewritten_query = result_text

        if rewritten_query == "":
            return {
                "pass_summarize": True,
                "summarized": True
            }
        else:
            return {
                "rewritten_query": rewritten_query,
                "pass_summarize": True,
                "summarized": True
            }
    except asyncio.TimeoutError:
        logger.error("Summarization timed out")
        return {
            "error": "Summarization timed out",
            "pass_summarize": True,
            "summarized": False
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error during summarization: {str(e)}")
        return {
            "error": str(e),
            "pass_summarize": True,
            "summarized": False
        }