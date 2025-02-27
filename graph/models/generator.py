# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

# llm = ChatOpenAI(temperature=0)
llm = ChatOllama(model="deepseek-coder:33b", temperature=0)

