from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The standalone query based on summary of the conversation"""
    new_query: str = Field(description="The standalone query")

system = """Summarize the intent from the user's input conversation into a standalone query.

RULES:
1. The more recent the message, the more weight it has.
2. Output ONLY the standalone query
3. Make the standalone query self-contained and clear
4. No quotes, prefixes, or explanations

"""

structured_llm = llm.with_structured_output(Summary)

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Input Conversation: {messages}<br>. {important_instructions}"),
    ]
)

summary_chain = summary_prompt | structured_llm
