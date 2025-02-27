from langchain_chroma import Chroma
from graph.models.embeddings import embeddings


def get_retriever(collection_name):
    return Chroma(
        collection_name=collection_name,
        persist_directory="./.chroma",
        embedding_function=embeddings,
    ).as_retriever()
