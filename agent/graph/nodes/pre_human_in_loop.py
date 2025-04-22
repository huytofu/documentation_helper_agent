from typing import Any, Dict
from agent.graph.state import GraphState
from copilotkit.langgraph import copilotkit_emit_state

async def pre_human_in_loop(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---PRE HUMAN IN LOOP---")
    if config:
        generating_state = {
            **state,
            "current_node": "PRE_HUMAN_IN_LOOP"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    need_human_feedback = state.get("need_human_feedback", False)
    received_human_feedback = state.get("received_human_feedback", False)
    return {"need_human_feedback": need_human_feedback, 
            "received_human_feedback": received_human_feedback}