from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm

class LanguageRoute(BaseModel):
    """Route a query to the appropriate programming language"""
    datasource: Literal["python", "javascript", "others", "none"] = Field(
        ...,
        description="""Given a user query determine which programming language is being discussed. 
        Answer must be either 'python', 'javascript', or 'others' or 'none' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=LanguageRoute)

# Create the prompt template
system = """You are an expert at identifying which programming language a user's query is about.

You must choose between:
- "python": For queries specifically about Python programming language, its libraries, frameworks, implementations
- "javascript": For queries specifically about JavaScript programming language, its libraries, frameworks, implementations
- "others": For queries about other programming languages besides Python and JavaScript
- "none": When the language is not specified or cannot be determined

(IMPORTANT!) Your answer must be either "python", "javascript", "others" or "none" only!

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
language_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(LanguageRoute) 