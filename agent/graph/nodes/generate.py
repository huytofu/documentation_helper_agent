from typing import Any, Dict
import asyncio
from agent.graph.chains.generation import generation_chain
from agent.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph.utils.message_utils import get_last_message_type, extract_output_state_properties
from langchain_core.documents import Document
from agent.graph.utils.message_utils import get_page_content
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import (
    handle_api_error,
    STANDARD_TIMEOUT,
    cost_tracker,
    APIResponse,
    GenerationResponse
)
import logging
logger = logging.getLogger(__name__)

async def generate(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---GENERATE---")
    # Emit only one "GENERATE" state update before generation
    if config:
        generating_state = {
            "current_node": "GENERATE",
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    query = state.get("query", "")
    documents = state.get("documents", [])
    framework = state.get("framework", "")
    language = state.get("language", "")
    retry_count = state.get("retry_count", 0)
    messages = state.get("messages", [])

    joined_documents = "\n\n".join([get_page_content(doc) for doc in documents[:3]])

    if framework and (framework not in ["none", ""]):
        extra_info = f"and is expert at the {framework} framework"
    else:
        extra_info = ""

    try:
        # Use asyncio to handle concurrent generation requests
        generation = await asyncio.wait_for(
            asyncio.to_thread(
                generation_chain.invoke,
                {
                    "language": language,
                    "extra_info": extra_info,
                    "documents": joined_documents,
                    "query": query
                }
            ),
            timeout=STANDARD_TIMEOUT
        )
        
        # Track API usage
        cost_tracker.track_usage(
            'generator',
            tokens=len(generation.split()),  # Approximate token count
            cost=0.0  # Update cost based on actual pricing
        )
        
        messages.append(AIMessage(content=generation))
        retry_count += 1

        return {
            "messages": messages,
            "retry_count": retry_count
        }
    except asyncio.TimeoutError:
        logger.error("Generation timed out")
        messages.append(AIMessage(content="BACKEND AGENT DEAD! Please try again later."))
        return {
            "messages": messages,
            "retry_count": retry_count,
            "error": "Generation timed out"
        }
    except Exception as e:
        logger.error(f"Error during generation: {str(e)}")
        messages.append(AIMessage(content="BACKEND AGENT DEAD! Please try again later."))
        return {
            "messages": messages,
            "retry_count": retry_count,
            "error": str(e)
        }
