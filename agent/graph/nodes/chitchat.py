from typing import Any, Dict
import asyncio
import logging

from langchain_core.messages import AIMessage
from agent.graph.state import GraphState
from agent.graph.chains.chitchat import invoke_chitchat
from agent.graph.utils.flow_state import reset_flow_state
from agent.graph.utils.api_utils import GENERATION_TIMEOUT, cost_tracker, standard_sleep
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state

logger = logging.getLogger(__name__)


async def chitchat(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Answer casual conversation and end the flow (no graders / HITL)."""
    print("---CHITCHAT---")
    if config:
        generating_state = {
            **state,
            "current_node": "CHITCHAT",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    query = state.get("query", "")

    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(invoke_chitchat, query),
            timeout=GENERATION_TIMEOUT,
        )
        cost_tracker.track_usage(
            "chitchat",
            tokens=len(reply.split()),
            cost=0.0,
            requests=1,
        )
        ai_message = AIMessage(
            content=reply,
            additional_kwargs={
                "display_in_chat": True,
                "error_type": None,
            },
        )
    except asyncio.TimeoutError:
        logger.error("Chitchat timed out")
        ai_message = AIMessage(
            content="I'm a bit slow right now — try again in a moment?",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "timeout",
                "error_message": "Chitchat timed out",
            },
        )
    except Exception as e:
        logger.error(f"Error during chitchat: {e}")
        ai_message = AIMessage(
            content="Something went wrong on my side. Mind saying that again?",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "internal",
                "error_message": str(e),
            },
        )
    finally:
        reset_flow_state()

    # Return only the new message — GraphState.messages uses add_messages.
    return {"messages": [ai_message], "current_node": "CHITCHAT"}
