from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm
from functools import lru_cache

class LanguageRoute(BaseModel):
    """Route a query to the appropriate programming language"""
    language: Literal["python", "javascript", "none", "others"] = Field(
        ...,
        description="""Answer options for: programming language that is mentioned in the query""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=LanguageRoute)

# Create the prompt template with optimized system message
system = """You are a programming language detection expert. Analyze the query and determine the mentioned programming language.
You must choose between four options:
- "python": Python-specific queries
- "javascript": JavaScript/TypeScript queries
- "none": No programming language mentioned
- "others": Other programming languages mentioned

You must not return any answer other than these four.

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
language_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(LanguageRoute)

@lru_cache(maxsize=1000)
def get_language_route(query: str) -> LanguageRoute:
    """Get the language route for a query with caching."""
    return language_router.invoke({"query": query}) 