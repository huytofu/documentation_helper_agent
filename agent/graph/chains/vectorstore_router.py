from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm
import hashlib
from functools import lru_cache

class VectorstoreRoute(BaseModel):
    """Route a query to the appropriate vectorstore"""
    datasource: Literal["openai", "smolagents", "langgraph", "copilotkit", "others"] = Field(
        ...,
        description="""Given a user query determine which vectorstore to use. 
        Answer must be either 'openai', 'smolagents', 'langgraph', 'copilotkit', or 'others' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=VectorstoreRoute)

# Create the prompt template
system = """You are an expert at routing a user query to the appropriate vectorstore.
We have three vectorstores available:
1. OpenAI vectorstore: Contains documentation about the OpenAI Agents SDK
2. SmolAgents vectorstore: Contains documentation about the SmolAgents framework
3. LangGraph vectorstore: Contains documentation about the LangGraph framework
4. CopilotKit vectorstore: Contains documentation about the CopilotKit framework and Coagents

Options:
- "openai": ONLY for queries specifically about the OpenAI Agents SDK
- "smolagents": ONLY for queries specifically about the SmolAgents framework
- "langgraph": ONLY for queries specifically about the LangGraph framework
- "copilotkit": ONLY for queries specifically about the CopilotKit framework and/or Coagents
- "others": For all other queries

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
vectorstore_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(VectorstoreRoute)

@lru_cache(maxsize=1000)
def get_vectorstore_route(query: str) -> VectorstoreRoute:
    """Get the vectorstore route for a query with caching."""
    return vectorstore_router.invoke({"query": query})