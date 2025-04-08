from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm

class RouteQuery(BaseModel):
    """Route a user query to a vectorstore or websearch"""
    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="""Answer options for: vectorstore or websearch""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=RouteQuery)

# Create the prompt template
system = """You are an expert at routing a user query to either a vectorstore or websearch.
Current vectorstores contain information about the OpenAI Agents SDK, Smolagents, Langgraph, 
and Copilokit framework which includes Coagents.

You must choose between two options:
- "vectorstore": ONLY for queries specifically about OpenAI Agents SDK, Smolagents, LangGraph, or CopilotKit (which includes Coagents) frameworks
- "websearch": For all other queries, including general programming questions, new technologies, other topics

You must not return any answer other than these two.

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
query_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(RouteQuery)