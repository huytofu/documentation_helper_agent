from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.summarizer import llm

system = """
    You are a master summarizer who is very good at summarizing a conversation between a user and an AI assistant.

    You are provided with the following set of messages:

    {messages}.

    Please help to rewrite the user's query into a standalone query based on your summary of the conversation.
    """
summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Messages: {messages}"),
    ]
)

summary_chain = summary_prompt | llm | StrOutputParser()
