from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from agent.graph.state import GraphState
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.api_utils import standard_sleep

async def pre_human_in_loop(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    print("---PRE HUMAN IN LOOP---")
    if config:
        generating_state = {
            **state,
            "current_node": "PRE_HUMAN_IN_LOOP"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()
        
    need_human_feedback = state.get("need_human_feedback", False)
    received_human_feedback = state.get("received_human_feedback", False)
    return {
        "need_human_feedback": need_human_feedback,
        "received_human_feedback": received_human_feedback,
        "current_node": "PRE_HUMAN_IN_LOOP",
    }
