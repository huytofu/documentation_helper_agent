"""Classify whether the user message is programming help or chitchat."""

from typing import Literal
from functools import lru_cache

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm


class IntentClassification(BaseModel):
    """Whether the user wants programming help or casual conversation."""

    intent: Literal["programming", "chitchat"] = Field(
        ...,
        description="programming for coding help; chitchat for small talk",
    )


parser = PydanticOutputParser(pydantic_object=IntentClassification)

system = """You classify the user's latest message as either programming help or chitchat.

You must set "intent" to exactly one of:
- "chitchat": greetings, small talk, asking for opinions rather than facts, jokes, how-are-you, thanks, or other non-technical conversation
- "programming": coding help, APIs, frameworks, packages, docs, build agents/apps, bugs, how-to code, documentation questions, or any technical/programming task

When unsure, prefer "programming".
When code excerpts/snippets are requested, prefer "programming".
When query mentions knowledge base, KB, chub, technical docs, vector stores/databases, indexed topics: prefer "programming".

VERY IMPORTANT: You must answer in JSON format that strictly follows the following schema:

{{
    "intent": your_selected_intent
}}

DO NOT RETURN ANY OTHER TEXT AFTER THE JSON.
"""

intent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

intent_classifier = intent_prompt | llm | parser


@lru_cache(maxsize=1000)
def get_intent(query: str) -> IntentClassification:
    """Cached intent classification for a query."""
    return intent_classifier.invoke({"query": query})
