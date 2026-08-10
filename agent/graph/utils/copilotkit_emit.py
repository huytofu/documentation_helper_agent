"""AG-UI-compatible manual emit helpers for CopilotKit / LangGraph nodes.

CopilotKit's ``copilotkit_emit_*`` helpers dispatch ``copilotkit_manually_emit_*``
event names. ``ag_ui_langgraph`` listens for ``manually_emit_message`` /
``manually_emit_state`` instead — use these wrappers so intermediate UI updates
work on the AG-UI path.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig


async def copilotkit_emit_state(config: RunnableConfig, state: Any) -> bool:
    """Emit intermediate state via the AG-UI ``manually_emit_state`` event."""
    await adispatch_custom_event(
        "manually_emit_state",
        state,
        config=config,
    )
    await asyncio.sleep(0.02)
    return True


async def copilotkit_emit_message(config: RunnableConfig, message: str) -> bool:
    """Emit a message via the AG-UI ``manually_emit_message`` event."""
    await adispatch_custom_event(
        "manually_emit_message",
        {"message": message, "message_id": str(uuid.uuid4()), "role": "assistant"},
        config=config,
    )
    await asyncio.shield(asyncio.sleep(0.02))
    return True
