from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm

system = """Extract and rewrite the user's intent from this conversation into a standalone query.

RULES:
1. Output ONLY the query - no other text
2. Make it self-contained and clear
3. No quotes, prefixes, or explanations

Example Output: How do I implement authentication in Flask

Conversation to analyze:
{messages}"""

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Rewrite as a single query. No explanations."),
    ]
)

summary_chain = summary_prompt | llm | StrOutputParser()
