from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.state import GraphState
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from copilotkit.langgraph import copilotkit_emit_state, copilotkit_emit_message
import asyncio

def convert_to_raw_documents(documents):
    """Convert LangChain documents to raw format."""
    raw_documents = []
    for doc in documents:
        if isinstance(doc, dict) and "lc" in doc:  # LangChain serialized format
            raw_doc = {
                "metadata": doc.get("kwargs", {}).get("metadata", {}),
                "page_content": doc.get("kwargs", {}).get("page_content", ""),
                "type": doc.get("kwargs", {}).get("type", "Document")
            }
        else:  # Already in raw format
            raw_doc = doc
        raw_documents.append(raw_doc)
    return raw_documents

async def immediate_message_two(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---IMMEDIATE MESSAGE 2---")
    messages = state.get("messages", [])
    comments = state.get("comments", "")
    documents = state.get("documents", [])

    # Convert documents to raw format
    raw_documents = convert_to_raw_documents(documents)

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
        messages.append(AIMessage(content=content))

    if config:
        generating_state = {
            **state,
            "current_node": "IMMEDIATE_MESSAGE_2",
            "documents": raw_documents  # Use raw documents in state
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await copilotkit_emit_message(config, content)
        #await asyncio.sleep(10)

    return {
        "messages": messages,
        "documents": raw_documents  # Return raw documents
    }