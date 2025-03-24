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
        description="""Given a user query determine which programming language is mentioned. 
        Answer must be either 'python', 'javascript', 'none' or 'others' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=LanguageRoute)

# Create the prompt template with optimized system message
system = """You are a language detection expert. Analyze the query and determine the programming language.
Options:
- "python": Python-specific queries
- "javascript": JavaScript/TypeScript queries
- "none": No language mentioned
- "others": Other programming languages

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
language_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(LanguageRoute)

# Add caching to the router
@lru_cache(maxsize=1000)
def cached_router(query: str) -> LanguageRoute:
    """Cached version of the router to avoid redundant LLM calls."""
    return language_router.invoke({"query": query})

# Update the router to use caching
language_router.invoke = cached_router 