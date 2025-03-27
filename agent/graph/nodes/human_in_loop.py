from typing import Any, Dict
from agent.graph.state import GraphState
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from copilotkit.langgraph import copilotkit_emit_state
import logging

logger = logging.getLogger(__name__)

async def human_in_loop(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    logger.info("---HUMAN IN LOOP---")
    messages = state.get("messages", [])
    last_message_type = get_last_message_type(messages)
    
    if last_message_type == "human":
        generation = ""
    elif last_message_type == "ai":
        generation = messages[-1].content
    
    # Create result state with current_node
    result_state = {
        "comments": "",  # Will be updated after interrupt
        "current_node": "HUMAN_IN_LOOP"
    }
    
    # Temporarily disabled explicit state emission
    # if config:
    #     output_properties = extract_output_state_properties(result_state)
    #     await copilotkit_emit_state(config, output_properties)
    
    human_in_loop = interrupt(
        "This is our generation: " + generation + 
        "But it may not answer your question.<br>" + 
        "Please provide a critical feedback on the generation.",
    )
    
    # Update result state with human input
    result_state["comments"] = human_in_loop
    
    return result_state