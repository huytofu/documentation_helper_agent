from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from agent.graph.models.generator import llm
from langsmith import Client
import os
import dotenv
dotenv.load_dotenv()

client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

try:
    generation_prompt = client.pull_prompt("generation_prompt")
except Exception as e:
    print("Error pulling prompt from Langsmith")
    print(e)
    system = """
        You are a master coder who is very good at coding {extra_info}.

        You are provided with the following set of technical documents:

        !START OF DOCUMENTS!
        {documents}.
        !END OF DOCUMENTS!

        Please refer to the provided documents to write code snippet(s) 
        to produce the feature or solve the problem described in the user's query.
        Try your best to answer in code. Do not return answers with only text.
        Please add some comments or explanations to help the user understand.
        
        Keep your code snippets to 100 lines or less.
        Keep your comments or explanations to 100 words or less.
        """
    generation_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Query: {query}"),
        ]
    )

generation_chain = generation_prompt | llm | StrOutputParser()
