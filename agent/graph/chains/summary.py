from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm
from pydantic import BaseModel, Field

class Summary(BaseModel):
    """The rewritten version of the human user's last message"""
    rewritten_query: str = Field(description="The rewritten version of the human user's last message")

system = """you are given an input conversation between a human user and an AI assistant.
Based on the conversation, rewrite the last message from the user into a more meaningful
& explicit query with better context while keeping the original meaning.

RULES:
1. If you are thinking and reasoning, you must not show your thinking or reasoning process to the user.
2. You must only respond with the rewritten query.
3. The rewritten query should be self-contained, clear and in English.
4. The rewritten query should not have any quotes, prefixes, or explanations.

{important_instructions}

{format_instructions}

"""

output_parser = PydanticOutputParser(pydantic_object=Summary)
format_instructions = output_parser.get_format_instructions()

# Create the chain with parsing
summary_chain = llm | output_parser

def clean_content(content):
    content = content.replace("{", "{{")
    content = content.replace("}", "}}")
    return content

def invoke_summary_chain(messages, instructions):
    summary_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            *[(message["role"], clean_content(message["content"])) for message in messages]
        ]
    ).partial(format_instructions=format_instructions)
    
    final_chain = summary_prompt | summary_chain

    return final_chain.invoke({"important_instructions": instructions})
