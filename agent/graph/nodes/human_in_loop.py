from typing import Any, Dict
from graph.state import GraphState
from langgraph.types import interrupt

def human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    human_in_loop = interrupt(
        "Please provide a response to the user's question.",
    )
    return {"comment": human_in_loop}