from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The rewritten query based on summarizing the conversation"""
    new_query: str = Field(description="The rewritten query")

system = """Extract and rewrite the user's intent from this conversation into a standalone query.

RULES:
1. Output ONLY the standalone query - no other text
2. Make the standalone query self-contained and clear
3. No quotes, prefixes, or explanations

Conversation to analyze:
{messages}"""

structured_llm = llm.with_structured_output(Summary)

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Rewrite as a single query. No explanations."),
    ]
)

summary_chain = summary_prompt | structured_llm
