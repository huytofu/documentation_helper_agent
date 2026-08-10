"""Helpers for streaming LangChain chains inside graph nodes."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from langchain_core.runnables import Runnable, RunnableConfig

from agent.graph.utils.api_utils import GENERATION_TIMEOUT


async def astream_chain_text(
    chain: Runnable,
    inputs: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    *,
    timeout: float = GENERATION_TIMEOUT,
) -> str:
    """Consume ``chain.astream`` and return concatenated text.

    Running the chain via ``astream`` (instead of ``invoke``) allows LangGraph /
    AG-UI to observe ``on_chat_model_stream`` token events.
    """
    parts: list[str] = []

    async def _consume() -> str:
        async for chunk in chain.astream(inputs, config=config):
            if chunk is None:
                continue
            parts.append(chunk if isinstance(chunk, str) else str(chunk))
        return "".join(parts)

    return await asyncio.wait_for(_consume(), timeout=timeout)
