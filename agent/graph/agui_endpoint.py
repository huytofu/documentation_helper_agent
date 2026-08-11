"""AG-UI FastAPI endpoint for LangGraphAGUIAgent (replaces CopilotKitRemoteEndpoint)."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, Optional, Union

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

CODING_AGENT_NAME = "coding_agent"
CODING_AGENT_DESCRIPTION = (
    "Expert coding agent that assists users with answering coding-related questions, "
    "code documentation, code completion and implementation."
)


def merge_run_input_state(
    input_data: RunAgentInput,
    properties: Optional[Dict[str, Any]],
) -> RunAgentInput:
    """Copy top-level properties into RunAgentInput.state (same semantics as api_utils)."""
    if not properties:
        return input_data
    state = dict(input_data.state or {})
    for key, value in properties.items():
        state[key] = value
    return input_data.model_copy(update={"state": state})


def build_coding_agent(
    graph: CompiledStateGraph,
    *,
    config: Union[Optional[RunnableConfig], dict] = None,
) -> LangGraphAGUIAgent:
    return LangGraphAGUIAgent(
        name=CODING_AGENT_NAME,
        description=CODING_AGENT_DESCRIPTION,
        graph=graph,
        config=config,
    )


async def create_agui_event_stream(
    agent: LangGraphAGUIAgent,
    input_data: RunAgentInput,
    accept: Optional[str],
) -> AsyncIterator[str]:
    encoder = EventEncoder(accept=accept)
    async for event in agent.run(input_data):
        if event is None:
            continue
        yield encoder.encode(event)


def register_agui_endpoint(
    app: FastAPI,
    graph: CompiledStateGraph,
    *,
    path: str = "/api/copilotkitagent",
    config: Union[Optional[RunnableConfig], dict] = None,
) -> LangGraphAGUIAgent:
    """Mount POST path that streams AG-UI events from LangGraphAGUIAgent.run()."""
    agent = build_coding_agent(graph, config=config)
    normalized = "/" + path.strip("/")

    @app.post(normalized)
    async def agui_agent_endpoint(request: Request):
        try:
            body = await request.json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Invalid AG-UI request body: %s", exc, exc_info=True)
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Request body must be JSON") from exc

        properties = body.pop("properties", None) if isinstance(body, dict) else None
        try:
            input_data = RunAgentInput.model_validate(body)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Invalid RunAgentInput: %s", exc, exc_info=True)
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=f"Invalid RunAgentInput: {exc}") from exc

        input_data = merge_run_input_state(input_data, properties)
        request_agent = agent.clone()
        accept_header = request.headers.get("accept")
        encoder = EventEncoder(accept=accept_header)

        async def event_generator():
            try:
                async for chunk in create_agui_event_stream(
                    request_agent, input_data, accept_header
                ):
                    yield chunk
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("AG-UI agent stream error: %s", exc, exc_info=True)
                raise

        return StreamingResponse(
            event_generator(),
            media_type=encoder.get_content_type(),
        )

    @app.get(f"{normalized}/health")
    def agui_health():
        return {"status": "ok", "agent": {"name": agent.name}}

    return agent
