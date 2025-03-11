from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agent.graph.models.router import llm

class LanguageRoute(BaseModel):
    """Route a query to the appropriate programming language"""
    datasource: Literal["python", "javascript", "others"] = Field(
        ...,
        description="""Given a user query determine which programming language is being discussed. 
        Answer must be either 'python', 'javascript' or 'others' only.""",
    )

# Create the output parser
parser = PydanticOutputParser(pydantic_object=LanguageRoute)

# Create the prompt template
system = """Identify which programming language is mentioned in the user's query.

You must choose between:
- "python": For queries mentioning Python programming language
- "javascript": For queries mentioning JavaScript programming language
- "others": When the programming language is not mentioned in query, or mentioned but is not Python or JavaScript


(IMPORTANT!) Your answer must be either "python", "javascript" or "others" only!

{format_instructions}"""

route_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{query}"),
])

# Create the chain with format instructions
language_router = route_prompt.partial(format_instructions=parser.get_format_instructions()) | llm.with_structured_output(LanguageRoute) 