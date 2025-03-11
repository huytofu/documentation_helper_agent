from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm

system = """
    You are a master coder who is very good at coding in {language} language {extra_info}. 
    You are given the following documents by the human user as parts of the documentation for the framework
    Please help write code snippet(s) using the documentations and your general coding knowledge
    to produce the feature or solve the problem described in the user's query.

    Please also consider previous generation and user's comments on it to improve the quality of your anwer
"""
generation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of documents: \n\n {documents} \n\n query: {query} \n\n Previous Generation: {generation} \n\n Comments: {comments}"),
    ]
)

generation_chain = generation_prompt | llm | StrOutputParser()
