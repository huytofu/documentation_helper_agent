from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The rewritten version of the human user's last message that is more meaningful"""
    rewritten_query: str = Field(description="The rewritten version of the human user's last message that is more meaningful")

system = """you are given an input conversation between a human user and an AI assistant.
Based on the conversation, rewrite the last message from the user into a more meaningful
standalone query with better context while keeping the original meaning.

RULES:
1. Messages in the conversation that are more recent are more important.
2. The rewritten query should be self-contained and clear and in English.
3. The rewritten query should not have any quotes, prefixes, or explanations.

{format_instructions}

"""

output_parser = PydanticOutputParser(pydantic_object=Summary)
format_instructions = output_parser.get_format_instructions()

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Input Conversation: {messages}<br>. {important_instructions}"),
    ]
).partial(format_instructions=format_instructions)

# Create the chain with parsing
summary_chain = summary_prompt | llm | output_parser
