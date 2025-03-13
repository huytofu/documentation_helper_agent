from typing import Any, Dict
from agent.graph.state import GraphState

def post_human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---POST HUMAN IN LOOP---")
    return {"current_node": "POST_HUMAN_IN_LOOP"}