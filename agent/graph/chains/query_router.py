from typing import Literal, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.router import llm

class RouteQuery(BaseModel):
    """Route a user query to a vectorstore or websearch"""

    datasource: Literal["vectorstore", "websearch", None] = Field(
        ...,
        description="""Given a user query determine whether to route it to a vectorstore or websearch. 
        Answer must be either 'vectorstore' or 'websearch' only.""",
    )

structured_llm_router = llm.with_structured_output(RouteQuery)

system = """You are an expert at routing a user query to either a vectorstore or websearch.
Current vectorstores contain information about the Langchain, Langgraph, 
and Copilokit framework which also includes knowledge about Coagents.
If the user query is not related to these topics, route it to a websearch.
(IMPORTANT!) Your answer must be either "vectorstore" or "websearch" only.
You must not return any answers other than these two.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

query_router = route_prompt | structured_llm_router