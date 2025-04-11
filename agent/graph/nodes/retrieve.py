from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.retrievers import get_retriever
from copilotkit.langgraph import copilotkit_emit_state

async def retrieve(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---RETRIEVE---")
    if config:
        generating_state = {
            "current_node": "RETRIEVE", **state
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    query = state.get("query", "")
    vectorstore = state.get("framework", None)
    if vectorstore in [None, "others"]:
        return {"documents": []}
    retriever = get_retriever(vectorstore)
    if retriever is None:
        return {"documents": []}
    else:
        documents = retriever.invoke(query)
        return {"documents": documents}