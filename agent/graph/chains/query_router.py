from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from graph.models.router import llm

class RouteQuery(BaseModel):
    """Route a user query to a vectorstore or websearch"""

    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="Given a user query determine whether to route it to a vector store or websearch.",
    )

structured_llm_router = llm.with_structured_output(RouteQuery)

system = """You are an expert at routing a user query to either a vectorstore or websearch.
Current vectorstores contain information about the Langchain, Langgraph, and Copilokit frameworks. 
Knowledge about Coagents is related to CopilotKit and is also available in the vectorstores.
If these topics are not relevant to the user query, route it to a websearch.
Your answer should be "vectorstore" or "websearch" only.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

query_router = route_prompt | structured_llm_router