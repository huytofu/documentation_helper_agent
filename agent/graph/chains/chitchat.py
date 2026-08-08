"""Casual conversational replies for non-programming user messages."""

from langchain_core.prompts import ChatPromptTemplate
from agent.graph.models.chitchat import llm

system = """You are a friendly, witty documentation helper agent having a brief casual conversation.
Reply naturally to the user. Do not invent programming tutorials unless they ask.
Keep replies concise (a few sentences unless the user clearly wants more).
"""

chitchat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

chitchat_chain = chitchat_prompt | llm


def invoke_chitchat(query: str) -> str:
    """Generate a chitchat reply for the user query."""
    result = chitchat_chain.invoke({"query": query})
    if hasattr(result, "content"):
        return result.content
    return str(result)
