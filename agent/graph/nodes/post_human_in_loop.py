from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from agent.graph.state import GraphState
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from langchain_core.messages import AIMessage
from agent.graph.utils.flow_state import reset_flow_state
from agent.graph.utils.api_utils import standard_sleep

async def post_human_in_loop(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    print("---POST HUMAN IN LOOP---")
    messages = state.get("messages", [])

    if config:
        generating_state = {
            **state,
            "current_node": "POST_HUMAN_IN_LOOP"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    updated_messages = []
    # Find and modify the last AI message (preserve id for add_messages upsert).
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            original = messages[i]
            original_content = original.content
            additional_kwargs = original.additional_kwargs
            new_content = (
                f"{original_content}\n\n"
                "Please be reminded that only last 8 messages are retained in chat to save token cost."
            )
            updated_messages = [
                AIMessage(
                    id=original.id,
                    content=new_content,
                    additional_kwargs=additional_kwargs,
                )
            ]
            break

    # Reset flow_state counters since we're at the end of the conversation
    reset_flow_state()
    print("Flow state counters reset")

    return {
        # Only the upserted AI message — GraphState.messages uses add_messages.
        "messages": updated_messages,
        "current_node": "POST_HUMAN_IN_LOOP",
    }
