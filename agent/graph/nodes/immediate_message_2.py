from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.state import GraphState
from typing import Dict, Any
from langchain_core.messages import SystemMessage

async def immediate_message_2(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    messages = state.get("messages", [])
    comments = state.get("comments", "")

    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        pass
    elif last_message_type == "ai":
        messages.append(SystemMessage(content=f"Seems like answer could me improved.\n\nHere are comments:\n{comments}\n\nPlease regenerate."))

    return {"messages": messages}