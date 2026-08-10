from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
import asyncio
import uuid
from agent.graph.chains.generation import generation_chain
from agent.graph.state import GraphState
from langchain_core.messages import AIMessage
from agent.graph.utils.message_utils import get_content
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state
from agent.graph.utils.api_utils import cost_tracker
from agent.graph.utils.message_utils import convert_to_raw_documents
from agent.graph.utils.api_utils import standard_sleep
from agent.graph.utils.stream_utils import astream_chain_text
import logging
logger = logging.getLogger(__name__)


def _assistant_message(content: str, *, message_id: Optional[str] = None, error_type=None, error_message=None) -> AIMessage:
    additional_kwargs = {
        "display_in_chat": True,
        "error_type": error_type,
    }
    if error_message is not None:
        additional_kwargs["error_message"] = error_message
    return AIMessage(
        id=message_id or str(uuid.uuid4()),
        content=content,
        additional_kwargs=additional_kwargs,
    )


async def generate(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    print("---GENERATE---")
    # Emit only one "GENERATE" state update before generation
    if config:
        generating_state = {
            **state,
            "current_node": "GENERATE"
        }
        # print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()
    rewritten_query = state.get("rewritten_query", "")
    documents = state.get("documents", [])
    framework = state.get("framework", "")

    raw_documents = convert_to_raw_documents(documents)

    joined_documents = "\n\n".join([get_content(doc) for doc in raw_documents[:3]])

    if framework and (framework not in ["none", ""]):
        extra_info = f"and is expert at the {framework} framework"
    else:
        extra_info = ""

    try:
        llm_generation, stream_message_id = await astream_chain_text(
            generation_chain,
            {
                "extra_info": extra_info,
                "documents": joined_documents,
                "query": rewritten_query,
            },
            config,
        )
        
        # Track API usage
        cost_tracker.track_usage(
            'generator',
            tokens=len(llm_generation.split()),  # Approximate token count
            cost=0.0,  # Update cost based on actual pricing
            requests=1
        )

        # Return only the new message — GraphState.messages uses add_messages.
        return {
            "messages": [_assistant_message(llm_generation, message_id=stream_message_id)],
            "documents": raw_documents,
            "current_node": "GENERATE",
        }
    except asyncio.TimeoutError:
        logger.error("Generation timed out")
        warning_message = "BACKEND AGENT DEAD! Please try again later."
        return {
            "messages": [_assistant_message(
                warning_message,
                error_type="timeout",
                error_message="Generation timed out",
            )],
            "documents": raw_documents,
            "error": "Generation timed out",
            "current_node": "GENERATE",
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error during generation: {str(e)}")
        warning_message = "BACKEND AGENT DEAD! Please try again later."
        return {
            "messages": [_assistant_message(
                warning_message,
                error_type="internal",
                error_message=str(e),
            )],
            "documents": raw_documents,
            "error": str(e),
            "current_node": "GENERATE",
        }
