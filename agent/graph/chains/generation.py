from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm

system = """
    You are a master coder who is very good at coding in {language} language {extra_info}. 
    You are given the following technical documents by the human user
    You are also given a user's query, a previous generation, and comments on the previous generation.
    Please help write code snippet(s) of maximum 100 lines using the documentations and your coding knowledge
    to produce the feature or solve the problem described in the user's query.

    (IMPORTANT!) Your answer must be in {language} language only!
    """
generation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Set of documents: \n\n {documents} \n\n Query: {query} \n\n Previous Generation: {generation} \n\n Comments: {comments}"),
    ]
)

generation_chain = generation_prompt | llm | StrOutputParser()
