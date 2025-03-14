from typing import Any, Dict
from agent.graph.state import GraphState
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type
import logging

logger = logging.getLogger(__name__)

def human_in_loop(state: GraphState) -> Dict[str, Any]:
    logger.info("---HUMAN IN LOOP---")
    messages = state["messages"]
    last_message_type = get_last_message_type(messages)
    
    if last_message_type == "human":
        generation = ""
    elif last_message_type == "ai":
        generation = messages[-1].get("content", "")
    
    human_in_loop = interrupt(
        "This is our generation: " + generation + 
        "But it may not answer your question.<br>" + 
        "Please provide a critical feedback on the generation.",
    )
    return {"comments": human_in_loop, "current_node": "HUMAN_IN_LOOP"}