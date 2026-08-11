"""Merged query + vectorstore router: one LLM call for datasource, language, and framework."""

from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.complex_router import llm


class RouteAndFramework(BaseModel):
    """Route a user query to websearch, vectorstore, chub, or direct generation."""

    datasource: Literal["vectorstore", "websearch", "direct", "kb_meta", "chub"] = Field(
        ...,
        description=(
            "vectorstore for indexed docs; websearch when external/current info is needed; "
            "direct for simple coding questions answerable from model knowledge alone; "
            "kb_meta when the user asks what this app's knowledge base contains; "
            "chub for library/package/SDK docs not yet indexed in the vectorstore catalog"
        ),
    )
    language: Literal["python", "javascript", "others", "none"] = Field(
        ...,
        description="Programming language mentioned in the query",
    )
    framework: Literal[
        "langgraph", "copilotkit", "chub", "others"
    ] = Field(
        ...,
        description=(
            "Pinecone namespace when datasource is vectorstore. "
            "Use others when datasource is websearch/direct or no namespace fits."
        ),
    )


parser = PydanticOutputParser(pydantic_object=RouteAndFramework)

system = """You are an expert at routing a user query to vectorstore, websearch, chub, or direct generation; detecting the programming language; and (when using the vectorstore) choosing the correct namespace.

You must set "datasource" to exactly one of (priority order):
- "kb_meta": ONLY when the user asks what THIS APP's knowledge base / indexed documentation contains (which frameworks or packages are indexed), not how to use a library
- "direct": simple coding questions/tasks answerable from model knowledge alone — short snippets, syntax, idioms, language builtins, trivial refactors — that do NOT need indexed docs, chub, or web search
- "vectorstore": queries about LangGraph, CopilotKit (including Coagents), or a package listed in the indexed chub packages catalog below
- "chub": library/package/SDK/API documentation questions that look like curated package guides, when the package is NOT in the indexed catalog below (so Pinecone retrieval would miss)
- "websearch": queries that need external or current information from the open web, or topics that are not package/library documentation shaped

EXAMPLES for datasource kb_meta (use kb_meta, framework="others"):
- "What documentation do you have indexed?"
- "Which packages are in your knowledge base?"
- "What frameworks can you retrieve docs for?"

Do NOT use kb_meta for how-to / API questions (use vectorstore/chub/websearch/direct as appropriate).

EXAMPLES for datasource chub (use chub, framework="others") — package/SDK docs NOT in the indexed catalog:
- "How do I authenticate with the foobar Python SDK?"
- "Show me pydantic-ai agent setup docs"
- "What are the main APIs in some-new-package?"

Do NOT use chub for news, current events, general web research, or non-package questions (use websearch).
Do NOT use chub when the package appears in the indexed catalog (use vectorstore + framework="chub" instead).

You must set "language" to exactly one of:
- "python": Python-specific queries
- "javascript": JavaScript/TypeScript-specific queries
- "none": No programming language explicitly mentioned
- "others": Another programming language like rust, go, C++, etc. is explicitly mentioned

EXAMPLES for language:
Even if you suspect that the query is about rust, answer with "others" only when the word "rust" appears in the query. If it doesn't, answer with "none".

When datasource is "vectorstore", set "framework" to exactly one of:
- "langgraph": ONLY for queries specifically about the LangGraph framework
- "copilotkit": ONLY for queries specifically about the CopilotKit framework and/or Coagents
- "chub": for library/SDK/API docs that are not framework-specific above — especially OpenAI, Pinecone, and other curated package guides already indexed
- "others": For queries that do not fit any documentation namespace above

When datasource is "websearch", "direct", "kb_meta", or "chub", set "framework" to "others".

Indexed packages currently available in the chub vectorstore namespace (from long-term memory):
{indexed_chub_packages}

If the user query is about one of those indexed chub packages (by doc id or title), prefer datasource="vectorstore" and framework="chub" instead of datasource="chub" or websearch.

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
