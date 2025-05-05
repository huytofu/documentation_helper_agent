from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm
from functools import lru_cache

class VectorstoreRoute(BaseModel):
    """Route a query to the appropriate choice of vectorstore"""
    datasource: Literal["openai", "smolagents", "langgraph", "copilotkit", "others"] = Field(
        ...,
        description="""Answer options for: choice of vectorstore""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=VectorstoreRoute)

# Create the prompt template
system = """You are an expert at deciding the most appropriate vectorstore to use for a given query.

You must choose between following five options. You must not select any option other than these five:
- "openai": ONLY for queries specifically about the OpenAI Agents SDK
- "smolagents": ONLY for queries specifically about the SmolAgents framework
- "langgraph": ONLY for queries specifically about the LangGraph framework
- "copilotkit": ONLY for queries specifically about the CopilotKit framework and/or Coagents
- "others": For all other queries

VERY IMPORTANT: You must answer in JSON format that strictly follows the following schema:

{{
    "datasource": your_selected_option
}}

"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
# vectorstore_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser
vectorstore_router = route_prompt | llm | parser
@lru_cache(maxsize=1000)
def get_vectorstore_route(query: str) -> VectorstoreRoute:
    """Get the vectorstore route for a query with caching."""
    return vectorstore_router.invoke({"query": query})