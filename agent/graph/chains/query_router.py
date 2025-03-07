from typing import Literal, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.router import llm

class RouteQuery(BaseModel):
    """Route a user query to a vectorstore or websearch"""

    datasource: Literal["vectorstore", "websearch", None] = Field(
        ...,
        description="Given a user query determine whether to route it to a vectorstore or websearch only.",
    )

structured_llm_router = llm.with_structured_output(RouteQuery)

system = """You are an expert at routing a user query to either a vectorstore or websearch.
Current vectorstores contain information about the Langchain, Langgraph, 
and Copilokit frameworks which includes knowledge about Coagents.
If these topics are not relevant to the user query, route it to a websearch.
Your answer must be a string that is either "vectorstore" or "websearch" only.
You must not return any other text or characters.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

query_router = route_prompt | structured_llm_router