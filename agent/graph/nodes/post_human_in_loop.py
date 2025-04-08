from typing import Any, Dict
from agent.graph.state import GraphState
from time import sleep

def post_human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---POST HUMAN IN LOOP---")
    # sleep(20)
    return {"current_node": "POST_HUMAN_IN_LOOP"}