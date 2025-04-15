from typing import Any, Dict
import asyncio
from agent.graph.chains.summary import summary_chain
from agent.graph.state import GraphState
from langchain_core.messages import AIMessage
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import (
    handle_api_error,
    cost_tracker,
)
import logging
logger = logging.getLogger(__name__)

# Define timeout for summarization (30 seconds as requested)
SUMMARIZE_TIMEOUT = 30

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

    messages = state.get("messages", [])

    try:
        # Use asyncio to handle concurrent summarization requests with timeout
        summary_result = await asyncio.wait_for(
            asyncio.to_thread(
                summary_chain.invoke,
                {
                    "messages": messages,
                    "important_instructions": instructions
                }
            ),
            timeout=SUMMARIZE_TIMEOUT
        )
        
        # Track API usage
        cost_tracker.track_usage(
            'summarizer',
            tokens=len(summary_result.new_query.split()),  # Approximate token count
            cost=0.0,  # Update cost based on actual pricing
            requests=1
        )

        # Update the query in state with the summarized result
        rewritten_query = summary_result.new_query

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