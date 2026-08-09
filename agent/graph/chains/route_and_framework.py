"""Merged query + vectorstore router: one LLM call for datasource, language, and framework."""

from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.complex_router import llm


class RouteAndFramework(BaseModel):
    """Route a user query to websearch, vectorstore, or direct generation."""

    datasource: Literal["vectorstore", "websearch", "direct"] = Field(
        ...,
        description=(
            "vectorstore for indexed docs; websearch when external/current info is needed; "
            "direct for simple coding questions answerable from model knowledge alone"
        ),
    )
    language: Literal["python", "javascript", "others", "none"] = Field(
        ...,
        description="Programming language mentioned in the query",
    )
    framework: Literal[
        "llamaindex", "smolagents", "langgraph", "copilotkit", "chub", "others"
    ] = Field(
        ...,
        description=(
            "Pinecone namespace when datasource is vectorstore. "
            "Use others when datasource is websearch/direct or no namespace fits."
        ),
    )


parser = PydanticOutputParser(pydantic_object=RouteAndFramework)

system = """You are an expert at routing a user query to vectorstore, websearch, or direct generation; detecting the programming language; and (when using the vectorstore) choosing the correct namespace.

You must set "datasource" to exactly one of:
- "vectorstore": queries about LlamaIndex, SmolAgents, LangGraph, CopilotKit (including Coagents), or related library/SDK docs we indexed into chub vectorstore (OpenAI API/SDK, Pinecone, and other curated package guides)
- "direct": simple coding questions/tasks answerable from model knowledge alone — short snippets, syntax, idioms, language builtins, trivial refactors — that do NOT need indexed docs or web search
- "websearch": queries that need external or current information, general programming beyond simple syntax/idioms, new technologies, or topics not covered by vectorstore/direct

You must set "language" to exactly one of:
- "python": Python-specific queries
- "javascript": JavaScript/TypeScript-specific queries
- "none": No programming language explicitly mentioned
- "others": Another programming language like rust, go, C++, etc. is explicitly mentioned

EXAMPLES for language:
Even if you suspect that the query is about rust, answer with "others" only when the word "rust" appears in the query. If it doesn't, answer with "none".

When datasource is "vectorstore", set "framework" to exactly one of:
- "llamaindex": ONLY for queries specifically about the LlamaIndex framework
- "smolagents": ONLY for queries specifically about the SmolAgents framework
- "langgraph": ONLY for queries specifically about the LangGraph framework
- "copilotkit": ONLY for queries specifically about the CopilotKit framework and/or Coagents
- "chub": for library/SDK/API docs that are not framework-specific above — especially OpenAI, Pinecone, and other curated package guides
- "others": For queries that do not fit any documentation namespace above

When datasource is "websearch" or "direct", set "framework" to "others".

Indexed packages currently available in the chub vectorstore namespace (from long-term memory):
{indexed_chub_packages}

If the user query is about one of those indexed chub packages (by doc id or title), prefer datasource="vectorstore" and framework="chub" instead of websearch.

VERY IMPORTANT: You must answer in JSON format that strictly follows the following schema:

{{
    "datasource": your_selected_datasource,
    "language": your_selected_language,
    "framework": your_selected_framework
}}

DO NOT RETURN ANY OTHER TEXT AFTER THE JSON.
"""

route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

route_and_framework_router = route_prompt | llm | parser


def get_route_and_framework(
    query: str, indexed_chub_packages: str = "(none indexed yet)"
) -> RouteAndFramework:
    """Merged route: datasource + language + framework in one LLM call.

    Not cached: indexed_chub_packages is dynamic and must affect later turns.
    """
    return route_and_framework_router.invoke(
        {
            "query": query,
            "indexed_chub_packages": indexed_chub_packages
            or "(none indexed yet)",
        }
    )
