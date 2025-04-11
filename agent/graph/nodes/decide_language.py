from typing import Any, Dict
from agent.graph.state import GraphState
from agent.graph.chains.language_router import get_language_route
from copilotkit.langgraph import copilotkit_emit_state

async def decide_language(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---DECIDE LANGUAGE---")
    if config:
        generating_state = {
            **state,
            "current_node": "DECIDE_LANGUAGE"
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    query = state.get("query", "")
    language = state.get("language", "")
    result = get_language_route(query)
    res_language = result.language
    
    if res_language in [None, "none"]:
        query = f"{query}. Please write code in {language} language"
        return {"language": language, "query": query}
    else:
        return {"language": res_language}