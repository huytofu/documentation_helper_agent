from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.router import llm

class RouteVectorstore(BaseModel):
    """Route a user query to the most relevant vectorstore."""

    datasource: Literal["langchain", "langgraph", "copilokit"] = Field(
        ...,
        description="Given a user query choose to route it to the most relevant vectorstore.",
    )

structured_llm_router = llm.with_structured_output(RouteVectorstore)

system = """You are an expert at routing a user query to a the most relevant vectorstore.
There are 3 vectorstores, each contains relevant documents about the Langchain, Langgraph, and Copilokit framework respectively.
Pick the most relevant vectorstore to route the user query to.
Your answer should be a string that is either "langchain" or "langgraph" or "copilokit" only.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

vectorstore_router = route_prompt | structured_llm_router