from typing import Any, Dict, Optional
import asyncio
import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agent.graph.state import GraphState
from agent.graph.chains.kb_meta import invoke_kb_meta
from agent.graph.stores import (
    CHUB_PACKAGES_NS,
    format_chub_packages_for_prompt,
    get_store,
)
from agent.graph.utils.flow_state import reset_flow_state
from agent.graph.utils.api_utils import GENERATION_TIMEOUT, cost_tracker, standard_sleep
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger(__name__)


async def _resolve_kb_catalog(
    state: GraphState, runtime: Optional[Runtime] = None
) -> str:
    catalog = (state.get("kb_catalog") or "").strip()
    if catalog:
        return catalog

    items = []
    store = getattr(runtime, "store", None) if runtime is not None else None
    if store is None:
        try:
            store = get_store()
        except Exception:
            logger.exception("kb_meta: failed to get store")
            store = None
    if store is not None:
        try:
            search = getattr(store, "asearch", None)
            if callable(search):
                items = await search(CHUB_PACKAGES_NS, limit=200)
            else:
                items = store.search(CHUB_PACKAGES_NS, limit=200)
        except Exception:
            logger.exception("kb_meta: chub package catalog read failed")
            items = []
    return format_chub_packages_for_prompt(items)


async def kb_meta(
    state: GraphState,
    runtime: Runtime = None,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """Answer meta questions about the KB catalog and end the flow."""
    print("---KB_META---")
    if config:
        generating_state = {
            **state,
            "current_node": "KB_META",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    query = state.get("query", "")
    kb_catalog = await _resolve_kb_catalog(state, runtime)

    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(invoke_kb_meta, query, kb_catalog),
            timeout=GENERATION_TIMEOUT,
        )
        cost_tracker.track_usage(
            "kb_meta",
            tokens=len(reply.split()),
            cost=0.0,
            requests=1,
        )
        ai_message = AIMessage(
            content=reply,
            additional_kwargs={
                "display_in_chat": True,
                "error_type": None,
            },
        )
    except asyncio.TimeoutError:
        logger.error("KB_META timed out")
        ai_message = AIMessage(
            content="I'm a bit slow right now — try again in a moment?",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "timeout",
                "error_message": "KB_META timed out",
            },
        )
    except Exception as e:
        logger.error(f"Error during KB_META: {e}")
        ai_message = AIMessage(
            content="Something went wrong on my side. Mind saying that again?",
            additional_kwargs={
                "display_in_chat": True,
                "error_type": "internal",
                "error_message": str(e),
            },
        )
    finally:
        reset_flow_state()

    return {
        "messages": [ai_message],
        "kb_catalog": kb_catalog,
        "current_node": "KB_META",
    }

