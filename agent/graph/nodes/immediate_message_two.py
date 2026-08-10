from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.state import GraphState
from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.api_utils import standard_sleep

async def immediate_message_two(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    print("---IMMEDIATE MESSAGE 2---")
    messages = state.get("messages", [])
    comments = state.get("comments", "")

    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        content = ""
        pass
    elif last_message_type == "ai":
        content = f'''
        SYSTEM: Seems like answer could me improved.
        SYSTEM: Here are user's comments:
        {comments}
        SYSTEM: Please regenerate.
        '''
        messages.append(SystemMessage(content=content))

    if config:
        generating_state = {
            **state,
            "current_node": "IMMEDIATE_MESSAGE_2"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()
        #await asyncio.sleep(10)

    return {
        "messages": messages,
        "current_node": "IMMEDIATE_MESSAGE_2",
    }
