from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm
from langsmith import Client
import os
import dotenv
dotenv.load_dotenv()

client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

try:
    regeneration_prompt = client.pull_prompt("regeneration_prompt")
except Exception as e:
    print("Error pulling prompt from Langsmith")
    print(e)

    system = """
        You are a master coder who is very good at coding {extra_info}.

        You are provided with the following set of technical documents:

        {documents}.

        You are also given the previous generation: 
        
        {generation}.

        You are also given comments on the previous generation: 
        
        {comments}.

        Please help revise or improve the previous generation according to the comments 
        to better address the user's query. The revised/improved answer must still refer
        to the provided documents.
        Keep your code snippets to 100 lines or less.
        Keep your comments or explanations to 100 words or less.
        """
    regeneration_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Query: {query}"),
        ]
    )

regeneration_chain = regeneration_prompt | llm | StrOutputParser()
