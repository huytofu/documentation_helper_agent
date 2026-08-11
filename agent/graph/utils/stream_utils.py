"""Helpers for streaming LangChain chains inside graph nodes."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple

from langchain_core.runnables import Runnable, RunnableConfig

from agent.graph.utils.api_utils import GENERATION_TIMEOUT


def _chunk_text(chunk: Any) -> str:
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


async def astream_chain_text(
    chain: Runnable,
    inputs: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
    *,
    timeout: float = GENERATION_TIMEOUT,
) -> Tuple[str, Optional[str]]:
    """Consume chat-model stream events; return (text, stream_message_id).

    Uses ``astream_events`` so AG-UI still sees ``on_chat_model_stream`` token
    events, while we capture the streamed message id for state correlation.
    """
    parts: list[str] = []
    message_id: Optional[str] = None

    async def _consume() -> Tuple[str, Optional[str]]:
        nonlocal message_id
        async for event in chain.astream_events(inputs, config=config, version="v2"):
            if event.get("event") != "on_chat_model_stream":
                continue
            chunk = (event.get("data") or {}).get("chunk")
            chunk_id = getattr(chunk, "id", None) if chunk is not None else None
            if chunk_id:
                message_id = str(chunk_id)
            text = _chunk_text(chunk)
            if text:
                parts.append(text)
        return "".join(parts), message_id

    return await asyncio.wait_for(_consume(), timeout=timeout)
