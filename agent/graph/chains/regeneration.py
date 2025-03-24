from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm

system = """
    You are a master coder who is very good at coding in {language} language {extra_info}.

    You are provided with the following set of technical documents:

    {documents}.

    You are also given the previous generation: 
    
    {generation}.

    You are also given comments on the previous generation: 
    
    {comments}.

    Please help revise or improve the answer to better address the user's query 
    based on the provided documents, the previous generation and the comments.
    """
regeneration_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Query: {query}"),
    ]
)

regeneration_chain = regeneration_prompt | llm | StrOutputParser()
