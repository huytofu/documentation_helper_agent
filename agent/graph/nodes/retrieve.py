from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from agent.graph.state import GraphState
from agent.graph.retrievers import get_retriever
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state, copilotkit_emit_message
from agent.graph.utils.api_utils import standard_sleep

async def retrieve(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    print("---RETRIEVE---")
    if config:
        generating_state = {
            **state,
            "current_node": "RETRIEVE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)   
        await copilotkit_emit_message(config, "Please wait while I retrieve useful context from knowledge base.")
        await standard_sleep()
        
    query = state.get("query", "")
    vectorstore = state.get("framework", None)
    if vectorstore in [None, "others"]:
        return {"documents": [], "current_node": "RETRIEVE"}
    retriever = get_retriever(vectorstore)
    if retriever is None:
        return {"documents": [], "current_node": "RETRIEVE"}
    else:
        documents = retriever.invoke(query)
        return {"documents": documents, "current_node": "RETRIEVE"}
