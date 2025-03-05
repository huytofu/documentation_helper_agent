# from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings

# embeddings = OpenAIEmbeddings()
embeddings = OllamaEmbeddings(model="deepseek-coder:33b")