from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.chains.language_router import language_router

def decide_language(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE LANGUAGE---")
    query = state["query"]
    language = state.get("language", "")
    result = language_router.invoke({"query": query})
    res_language = result.language
    if res_language is None:
        return {"language": language, "current_node": "DECIDE_LANGUAGE"}
    elif res_language == "none":
        return {"language": language, "current_node": "DECIDE_LANGUAGE"}
    else:
        return {"language": res_language, "current_node": "DECIDE_LANGUAGE"}