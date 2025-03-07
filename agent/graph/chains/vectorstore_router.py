from typing import Literal, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from agent.graph.models.router import llm

class RouteVectorstore(BaseModel):
    """Route a user query to the most relevant vectorstore."""

    datasource: Literal["langchain", "langgraph", "copilokit", None] = Field(
        ...,
        description="""Given a user query choose to route it to the most relevant vectorstore.
        Answer must be either 'langchain' or 'langgraph' or 'copilokit' only.""",
    )

structured_llm_router = llm.with_structured_output(RouteVectorstore)

system = """You are an expert at routing a user query to a the most relevant vectorstore.
There are 3 vectorstores, each contains relevant documents about the Langchain, Langgraph, and Copilokit framework respectively.
Pick the most relevant vectorstore to route the user query to.
(IMPORTANT!) Your answer must be either "langchain" or "langgraph" or "copilokit" only.
You must not return any other values besides these three.
"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

vectorstore_router = route_prompt | structured_llm_router