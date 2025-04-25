from typing import Any, Dict
from agent.graph.state import GraphState
from copilotkit.langgraph import copilotkit_emit_state
from langchain_core.messages import AIMessage
from agent.graph.utils.flow_state import reset_flow_state

async def post_human_in_loop(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---POST HUMAN IN LOOP---")
    messages = state.get("messages", [])

    if config:
        generating_state = {
            **state,
            "current_node": "POST_HUMAN_IN_LOOP"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    # Find and modify the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Get the original content
            original_content = messages[i].content
            additional_kwargs = messages[i].additional_kwargs
            # Create new content with the reminder
            new_content = f"{original_content}\n\nPlease be reminded that only last 8 messages are retained in chat to save token cost."
            # Replace the message with updated content
            messages[i] = AIMessage(
                content=new_content,
                additional_kwargs=additional_kwargs
            )
            break

    # Reset flow_state counters since we're at the end of the conversation
    reset_flow_state()
    print("Flow state counters reset")

    return {
        "messages": messages
    }