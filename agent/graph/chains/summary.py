from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The standalone query based on summary of the conversation"""
    new_query: str = Field(description="The standalone query")

system = """you are given an input conversation between a human user and an AI assistant.
Summarize the conversation into a standalone query as if asked by the user.

RULES:
1. The more recent the message in the conversation, the more weight it has.
2. Messages from the human user has more weight than the AI assistant.
3. Output ONLY the standalone query without any quotes, prefixes, or explanations.
4. Make the standalone query self-contained and clear

"""

structured_llm = llm.with_structured_output(Summary)

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Input Conversation: {messages}<br>. {important_instructions}"),
    ]
)

summary_chain = summary_prompt | structured_llm
