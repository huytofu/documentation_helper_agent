from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from graph.models.router import llm

class RouteLanguage(BaseModel):
    """Route a user query to the most relevant language."""

    datasource: Literal["python", "javascript"] = Field(
        ...,
        description="Given a user query choose to route it to the most relevant language.",
    )

structured_llm_router = llm.with_structured_output(RouteLanguage)

system = """You are an expert at routing a user query to a the most relevant language.
Languages are coding languages like Python and Javascript.
Pick the most relevant language to route the user query to.
Your answer should be "python" or "javascript" or "other" only.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

language_router = route_prompt | structured_llm_router