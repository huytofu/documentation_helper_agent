"""Soft-refuse browsing large framework namespaces wholesale."""

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from agent.graph.state import GraphState
from agent.graph.utils.flow_state import reset_flow_state
from agent.graph.utils.api_utils import standard_sleep
from agent.graph.utils.copilotkit_emit import copilotkit_emit_state


_REFUSE_TEMPLATE = (
    "{label} is a large indexed documentation corpus, so I can't dump it all at once. "
    "Ask a specific question about it and I'll retrieve the most relevant sections."
)


async def browse_refuse(
    state: GraphState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Explain that large namespaces cannot be dumped; end the flow."""
    print("---BROWSE_REFUSE---")
    if config:
        generating_state = {
            **state,
            "current_node": "BROWSE_REFUSE",
        }
        await copilotkit_emit_state(config, generating_state)
        await standard_sleep()

    framework = (state.get("framework") or "").strip()
    label = framework if framework and framework not in ("others", "none") else "That namespace"

    ai_message = AIMessage(
        content=_REFUSE_TEMPLATE.format(label=label),
        additional_kwargs={
            "display_in_chat": True,
            "error_type": None,
        },
    )
    reset_flow_state()
    return {
        "messages": [ai_message],
        "current_node": "BROWSE_REFUSE",
    }
