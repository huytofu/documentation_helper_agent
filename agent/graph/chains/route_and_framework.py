"""Merged query + vectorstore router: one LLM call for datasource and framework."""

from typing import Literal
from functools import lru_cache

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm


class RouteAndFramework(BaseModel):
    """Route a user query to websearch or a documentation vectorstore namespace."""

    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="vectorstore for indexed docs; websearch for everything else",
    )
    framework: Literal[
        "llamaindex", "smolagents", "langgraph", "copilotkit", "chub", "others"
    ] = Field(
        ...,
        description=(
            "Pinecone namespace when datasource is vectorstore. "
            "Use others when datasource is websearch or no namespace fits."
        ),
    )


parser = PydanticOutputParser(pydantic_object=RouteAndFramework)

system = """You are an expert at routing a user query to either websearch or a documentation vectorstore, and (when using the vectorstore) choosing the correct namespace.

You must set "datasource" to exactly one of:
- "vectorstore": queries about LlamaIndex, SmolAgents, LangGraph, CopilotKit (including Coagents), or related library/SDK docs we index (OpenAI API/SDK, Pinecone, and other curated package guides)
- "websearch": all other queries, including general programming questions, new technologies, other topics

When datasource is "vectorstore", set "framework" to exactly one of:
- "llamaindex": ONLY for queries specifically about the LlamaIndex framework
- "smolagents": ONLY for queries specifically about the SmolAgents framework
- "langgraph": ONLY for queries specifically about the LangGraph framework
- "copilotkit": ONLY for queries specifically about the CopilotKit framework and/or Coagents
- "chub": for library/SDK/API docs that are not framework-specific above — especially OpenAI, Pinecone, and other curated package guides from the chub knowledge base
- "others": For queries that do not fit any documentation namespace above

When datasource is "websearch", set "framework" to "others".

VERY IMPORTANT: You must answer in JSON format that strictly follows the following schema:

{{
    "datasource": your_selected_datasource,
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


@lru_cache(maxsize=1000)
def get_route_and_framework(query: str) -> RouteAndFramework:
    """Cached merged route: datasource + framework in one LLM call."""
    return route_and_framework_router.invoke({"query": query})
