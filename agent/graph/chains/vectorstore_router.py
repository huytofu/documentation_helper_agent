from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm

class VectorstoreRoute(BaseModel):
    """Route a query to the appropriate vectorstore"""
    datasource: Literal["langchain", "langgraph", "copilotkit"] = Field(
        ...,
        description="""Given a user query determine which vectorstore to use. 
        Answer must be either 'langchain', 'langgraph', or 'copilotkit' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=VectorstoreRoute)

# Create the prompt template
system = """You are an expert at routing a user query to the appropriate vectorstore.
We have three vectorstores available:
1. LangChain vectorstore: Contains documentation about the LangChain framework
2. LangGraph vectorstore: Contains documentation about the LangGraph framework
3. CopilotKit vectorstore: Contains documentation about the CopilotKit framework and Coagents

You must choose between:
- "langchain": ONLY for queries specifically about LangChain
- "langgraph": ONLY for queries specifically about LangGraph
- "copilotkit": ONLY for queries specifically about CopilotKit and/or Coagents

(IMPORTANT!) Your answer must be either "langchain", "langgraph", or "copilotkit" only.

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
vectorstore_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(VectorstoreRoute)