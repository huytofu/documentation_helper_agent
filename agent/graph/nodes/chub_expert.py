from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command, interrupt
from copilotkit.langgraph import copilotkit_emit_message, copilotkit_emit_state

from agent.graph.chains.chub_expert import (
    CHUB_EXPERT_SYSTEM,
    harvest_chub_documents,
    llm_with_tools,
)
from agent.graph.consts import ASK_CHUB_PERMISSION, CHUB_EXPERT, GENERATE
from agent.graph.state import GraphState
from agent.graph.utils.api_utils import standard_sleep

CHUB_CONSENT_PROMPT = (
    "Pinecone retrieval found no useful docs. "
    "Is it OK for the agent to use chub tools to search for better context? "
    "Reply yes or no."
)


def _seed_messages(state: GraphState) -> List[Any]:
    query = state.get("query", "")
    language = state.get("language", "python")
    return [
        SystemMessage(content=CHUB_EXPERT_SYSTEM),
        HumanMessage(
            content=(
                f"User query: {query}\n"
                f"Language hint: {language}\n"
                "Find and fetch the most relevant chub documentation."
            )
        ),
    ]


async def ask_chub_permission(
    state: GraphState, config: Dict[str, Any] = None
) -> Command[Literal["ask_chub_permission", "chub_expert", "generate"]]:
    """HITL yes/no before chub tools. Routes only via Command (no outgoing edges)."""
    print("---ASK CHUB PERMISSION---")
    if config:
        await copilotkit_emit_state(
            config,
            {
                **state,
                "current_node": "ASK_CHUB_PERMISSION",
                "pending_question": state.get("pending_question"),
            },
        )
        await standard_sleep()

    pending_question: Optional[str] = state.get("pending_question")
    # First ask: pending_question is null (UI / emit shows the default consent prompt).
    # Retry after invalid answer: pending_question is "Please choose yes or no".
    answer = interrupt(pending_question or CHUB_CONSENT_PROMPT)
    normalized = str(answer).strip().lower()

    if normalized == "no":
        return Command(
            goto=GENERATE,
            update={
                "chub_enrich_attempted": True,
                "chub_consent": False,
                "pending_question": None,
            },
        )

    if normalized != "yes":
        return Command(
            goto=ASK_CHUB_PERMISSION,
            update={
                "pending_question": "Please choose yes or no",
                "chub_enrich_attempted": True,
            },
        )

    return Command(
        goto=CHUB_EXPERT,
        update={
            "chub_consent": True,
            "chub_enrich_attempted": True,
            "pending_question": None,
        },
    )


async def chub_expert(
    state: GraphState, config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Tool-bound chub expert LLM turn (consent handled by ASK_CHUB_PERMISSION)."""
    print("---CHUB EXPERT---")
    if config:
        await copilotkit_emit_state(
            config,
            {
                **state,
                "current_node": "CHUB_ENRICH",
                "pending_question": state.get("pending_question"),
            },
        )
        await standard_sleep()

    prior = list(state.get("chub_messages") or [])
    if not prior:
        invoke_messages = _seed_messages(state)
        response = llm_with_tools.invoke(invoke_messages)
        new_messages = invoke_messages + [response]
        full_transcript = new_messages
    else:
        response = llm_with_tools.invoke(prior)
        new_messages = [response]
        full_transcript = prior + [response]

    updates: Dict[str, Any] = {
        "chub_messages": new_messages,
        "chub_enrich_attempted": True,
        "chub_consent": True,
        "pending_question": None,
    }

    harvested = harvest_chub_documents(full_transcript)
    if harvested:
        updates["documents"] = harvested

    # When the expert finishes (no more tool_calls), append a short summary.
    if not getattr(response, "tool_calls", None):
        if config:
            await copilotkit_emit_message(config, "Chub research done!")

    return updates


async def chub_tools(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute pending tool_calls via ToolNode; emit each tool name for UX."""
    print("---CHUB TOOLS---")
    from agent.graph.chains.chub_expert import chub_tool_node

    if config:
        await copilotkit_emit_state(
            config,
            {
                **state,
                "current_node": "CHUB_ENRICH",
            },
        )
        await standard_sleep()

    # Tiny CopilotKit message per tool name about to run this round.
    msgs = state.get("chub_messages") or []
    last = msgs[-1] if msgs else None
    tool_calls = getattr(last, "tool_calls", None) if last is not None else None
    if config and tool_calls:
        for call in tool_calls:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if name:
                await copilotkit_emit_message(config, "Calling chub tool: " + str(name))

    rounds = int(state.get("chub_tool_rounds") or 0) + 1
    tool_updates = chub_tool_node.invoke(state)
    return {
        **tool_updates,
        "chub_tool_rounds": rounds,
    }
