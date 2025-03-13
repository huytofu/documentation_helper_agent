from typing import Any, Dict
from agent.graph.state import GraphState

def pre_human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---PRE HUMAN IN LOOP---")
    return {"current_node": "PRE_HUMAN_IN_LOOP"}