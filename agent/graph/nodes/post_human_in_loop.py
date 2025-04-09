from typing import Any, Dict
from agent.graph.state import GraphState
from time import sleep
from copilotkit.langgraph import copilotkit_emit_state
from langchain_core.messages import AIMessage

async def post_human_in_loop(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---POST HUMAN IN LOOP---")
    messages = state.get("messages", [])

    if config:
        generating_state = {
            "current_node": "POST_HUMAN_IN_LOOP",
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    # Find and modify the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Get the original content
            original_content = messages[i].content
            # Create new content with the reminder
            new_content = f"{original_content}\n\nPlease be reminded that only last 8 messages are retained in chat to save token cost."
            # Replace the message with updated content
            messages[i] = AIMessage(content=new_content)
            break

    return {
        "messages": messages
    }