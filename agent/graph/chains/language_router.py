from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm
from functools import lru_cache

class LanguageRoute(BaseModel):
    """Route a query to the appropriate programming language"""
    language: Literal["python", "javascript", "others", "none"] = Field(
        ...,
        description="""Answer options for: programming language that is mentioned in the query""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=LanguageRoute)

# Create the prompt template with optimized system message
system = """You are a programming language detection expert. Analyze the query and determine the mentioned programming language.

You must choose between following four options. You must not select any option other than these four:
- "python": Python-specific queries
- "javascript": JavaScript/TypeScript queries
- "others": Another programming language (that is not python or javascript) is specifically mentioned
- "none": No programming language mentioned

VERY IMPORTANT: You must answer in JSON format that strictly follows the following schema:

{{
    "language": your_selected_option
}}

"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
# language_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser
language_router = route_prompt | llm | parser

@lru_cache(maxsize=1000)
def get_language_route(query: str) -> LanguageRoute:
    """Get the language route for a query with caching."""
    return language_router.invoke({"query": query}) 