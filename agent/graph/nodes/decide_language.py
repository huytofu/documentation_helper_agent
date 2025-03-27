from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.chains.language_router import get_language_route

def decide_language(state: GraphState) -> Dict[str, Any]:
    print("---DECIDE LANGUAGE---")
    query = state.get("query", "")
    language = state.get("language", "")
    result = get_language_route(query)
    res_language = result.language
    if res_language is None:
        return {"language": language, "current_node": "DECIDE_LANGUAGE"}
    elif res_language == "none":
        return {"language": language, "current_node": "DECIDE_LANGUAGE"}
    else:
        return {"language": res_language, "current_node": "DECIDE_LANGUAGE"}