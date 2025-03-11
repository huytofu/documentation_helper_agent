from typing import Any, Dict
from agent.graph.state import GraphState
from langgraph.types import interrupt

def human_in_loop(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE---")
    final_generation = state["generation"].replace("\n", "<br>")
    human_in_loop = interrupt(
        "This is our generation: " + final_generation + 
        "But it may not answer your question.<br>" + 
        "Please provide a critical feedback on the generation.",
    )
    return {"comments": human_in_loop, "final_generation": final_generation}