from typing import Any, Dict
from graph.state import GraphState

def human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    human_in_loop = None
    return {"comment": human_in_loop}