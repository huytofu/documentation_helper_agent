from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field
import json

class Summary(BaseModel):
    """The output query which is a more meaningful rewritten version of the human user's last message"""
    rewritten_query: str = Field(description="The output query which is a more meaningful version of the human user's last message")

system = """you are given an input conversation between a human user and an AI assistant.
Based on the conversation, rewrite the last message from the user into a more meaningful
standalone query with better context while keeping the original meaning.

RULES:
1. Messages in the conversation that are more recent are more important.
2. The rewritten query should be self-contained and clear.
3. The rewritten query should not have any quotes, prefixes, or explanations.
4. You MUST output in the following JSON format:
{
    "rewritten_query": "your rewritten query here"
}

"""

def parse_summary(text: str) -> Summary:
    try:
        # Try to parse as JSON first
        data = json.loads(text)
        return Summary(**data)
    except json.JSONDecodeError:
        # If not JSON, wrap the text in the required format
        return Summary(rewritten_query=text.strip())

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Input Conversation: {messages}<br>. {important_instructions}"),
    ]
)

# Create the chain with parsing
summary_chain = summary_prompt | llm | parse_summary
