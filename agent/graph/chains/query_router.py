from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm

class RouteQuery(BaseModel):
    """Route a user query to a vectorstore or websearch"""
    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="""Given a user query determine whether to route it to a vectorstore or websearch. 
        Answer must be either 'vectorstore' or 'websearch' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=RouteQuery)

# Create the prompt template
system = """You are an expert at routing a user query to either a vectorstore or websearch.
Current vectorstores contain information about the Langchain, Langgraph, 
and Copilokit framework which also includes knowledge about Coagents.

You must choose between:
- "vectorstore": ONLY for queries specifically about LangChain, LangGraph, or CopilotKit (which includes Coagents) frameworks and their features
- "websearch": For all other queries, including general programming questions, new technologies, or any other topics

(IMPORTANT!) Your answer must be either "vectorstore" or "websearch" only.
You must not return any answers other than these two.

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
query_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(RouteQuery)