from typing import Any, Dict
from graph.state import GraphState
from graph.chains.language_router import language_router

def decide_language(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE LANGUAGE---")
    query = state["query"]
    language = language_router.invoke({"query": query})
    return {"language": language}