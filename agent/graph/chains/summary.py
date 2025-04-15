from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The output query which is a more meaningful rewritten version of the human user's last message"""
    rewritten_query: str = Field(description="The output query which is a more meaningful version of the human user's last message")

system = """you are given an input conversation between a human user and an AI assistant.
Based on the conversation, rewrite the last message from the user into a more meaningful
standalone query with better context while keeping the original meaning.

RULES:
1. Messages in the conversation that are more recent are more important.
2. Output ONLY the rewritten standalone query.
3. The output should be self-contained and clear.
4. The output should not have any quotes, prefixes, or explanations.

"""

structured_llm = llm.with_structured_output(Summary)

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Input Conversation: {messages}<br>. {important_instructions}"),
    ]
)

summary_chain = summary_prompt | structured_llm
