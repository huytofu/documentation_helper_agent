from typing import Any, Dict
from agent.graph.state import GraphState
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage

def human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---HUMAN IN LOOP---")
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.type == "human" or isinstance(last_message, HumanMessage):
        generation = ""
    elif last_message.type == "ai" or isinstance(last_message, AIMessage):
        generation = last_message.get("content", "")
    human_in_loop = interrupt(
        "This is our generation: " + generation + 
        "But it may not answer your question.<br>" + 
        "Please provide a critical feedback on the generation.",
    )
    return {"comments": human_in_loop, "current_node": "HUMAN_IN_LOOP"}