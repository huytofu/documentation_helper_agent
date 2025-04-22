from typing import Any, Dict
from agent.graph.state import GraphState
from langgraph.types import interrupt
from copilotkit.langgraph import copilotkit_emit_state
import logging

logger = logging.getLogger(__name__)

async def human_in_loop(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    logger.info("---HUMAN IN LOOP---")
    if config:
        generating_state = {
            **state,
            "current_node": "HUMAN_IN_LOOP"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    
    # Create result state with current_node
    result_state = {
        "comments": "",  # Will be updated after interrupt
    }
    
    human_in_loop = interrupt(
        "We have an answer to your question.\n" + 
        "But it may not answer your question.\n" + 
        "Please provide a critical feedback on the generation.\n"
    )
    
    # Update result state with human input
    result_state["comments"] = human_in_loop
    result_state["received_human_feedback"] = True
    
    return result_state