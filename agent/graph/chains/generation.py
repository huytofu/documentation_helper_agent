from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm

system = """
    You are a master coder who is very good at coding {extra_info}.

    You are provided with the following set of technical documents:

    {documents}.

    Please help write code snippet(s) of maximum 200 lines using the provided documents
    to produce the feature or solve the problem described in the user's query. 
    Please add some comments or explanations to help the user understand.
    """
generation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Query: {query}"),
    ]
)

generation_chain = generation_prompt | llm | StrOutputParser()
