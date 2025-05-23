from typing import Any, Dict
import asyncio

from agent.graph.chains.regeneration import regeneration_chain
from agent.graph.state import GraphState
from langchain_core.messages import AIMessage
from agent.graph.utils.message_utils import get_last_message_type
from agent.graph.utils.message_utils import get_content
from copilotkit.langgraph import copilotkit_emit_state
from agent.graph.utils.api_utils import (
    GENERATION_TIMEOUT,
    cost_tracker,
)
from agent.graph.utils.message_utils import convert_to_raw_documents
from agent.graph.utils.api_utils import standard_sleep
import logging
logger = logging.getLogger(__name__)


async def regenerate(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    print("---REGENERATE---")
    
    # Get state variables
    rewritten_query = state.get("rewritten_query", "")
    documents = state.get("documents", [])
    framework = state.get("framework", "")
    messages = state.get("messages", [])

    # Convert documents to raw format
    raw_documents = convert_to_raw_documents(documents)
    
    if config:
        generating_state = {
            **state,
            "current_node": "REGENERATE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()
    last_message_type = get_last_message_type(messages)
    if last_message_type == "human":
        generation = ""
    elif last_message_type == "ai":
        generation = messages[-1].content
        
    
    comments = state.get("comments", "")

    joined_documents = "\n\n".join([get_content(doc) for doc in raw_documents[:3]])

    if framework and (framework not in ["none", ""]):
        extra_info = f"and is expert at the {framework} framework"
    else:
        extra_info = ""

    try:
        # Use asyncio to handle concurrent generation requests
        llm_generation = await asyncio.wait_for(
            asyncio.to_thread(
                regeneration_chain.invoke,
                {
                    "extra_info": extra_info,
                    "documents": joined_documents,
                    "query": rewritten_query,
                    "generation": generation,
                    "comments": comments
                }
            ),
            timeout=GENERATION_TIMEOUT
        )
        
        # Track API usage
        cost_tracker.track_usage(
            'generator',
            tokens=len(llm_generation.split()),  # Approximate token count
            cost=0.0,  # Update cost based on actual pricing
            requests=1
        )
        
        messages.append(AIMessage(
            content=llm_generation,
            additional_kwargs={
                "display_in_chat": True,
                "error_type": None
            }
        ))

        return {
            "messages": messages,
            "documents": raw_documents
        }
    except asyncio.TimeoutError:
        logger.error("Generation timed out")
        messages.append(AIMessage(
            content="BACKEND AGENT DEAD! Please try again later.",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "timeout",
                "error_message": "Generation timed out"
            }
        ))
        return {
            "messages": messages,
            "documents": raw_documents,
            "error": "Generation timed out"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error during generation: {str(e)}")
        messages.append(AIMessage(
            content="BACKENDS AGENT DEAD! Please try again later.",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "internal",
                "error_message": str(e)
            }
        ))
        return {
            "messages": messages,
            "documents": raw_documents,
            "error": str(e)
        }
