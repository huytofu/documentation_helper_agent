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
system = """You are an expert at routing a user query to either a vectorstore or websearch or none.

You must choose between following two options. You must not select any option other than these two:
- "vectorstore": ONLY for queries specifically about LlamaIndex, Smolagents, LangGraph, or CopilotKit (which includes Coagents) frameworks
- "websearch": For all other queries, including general programming questions, new technologies, other topics

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
# query_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser
query_router = route_prompt | llm | parser