from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.state import GraphState
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from copilotkit.langgraph import copilotkit_emit_state
import asyncio

async def immediate_message_one(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---IMMEDIATE MESSAGE 1---")
    messages = state.get("messages", [])

    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        content = ""
        pass
    elif last_message_type == "ai":
        content = "SYSTEM: Seems like answer not grounded in the documents. Please regenerate."
        messages.append(HumanMessage(content=content))

    if config:
        generating_state = {
            "current_node": "IMMEDIATE_MESSAGE_1",
            "last_message_content": content,
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    #await asyncio.sleep(10)
    return {"messages": messages}