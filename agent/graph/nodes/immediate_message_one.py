from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.state import GraphState
from typing import Dict, Any
from langchain_core.messages import AIMessage
from copilotkit.langgraph import copilotkit_emit_state, copilotkit_emit_message
from agent.graph.utils.api_utils import standard_sleep

async def immediate_message_one(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---IMMEDIATE MESSAGE 1---")
    messages = state.get("messages", [])

    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        content = ""
        pass
    elif last_message_type == "ai":
        content = '''
        SYSTEM: Seems like answer not grounded in the documents.
        SYSTEM: Please regenerate.
        '''
        messages.append(AIMessage(content=content))

    if config:
        generating_state = {
            **state,
            "current_node": "IMMEDIATE_MESSAGE_1"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await copilotkit_emit_message(config, content)
        await standard_sleep()
        # await asyncio.sleep(10)

    return {"messages": messages}