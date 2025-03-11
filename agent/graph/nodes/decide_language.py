from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.chains.language_router import language_router

def decide_language(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE LANGUAGE---")
    query = state["query"]
    language = state.get("language", "")
    result = language_router.invoke({"query": query})
    if result.datasource == "none":
        return {"language": language}
    else:
        return {"language": result.datasource or language}