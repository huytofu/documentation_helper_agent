from langchain_chroma import Chroma
from graph.models.embeddings import embeddings


def get_retriever(collection_name, language):
    try:
        if language == "other":
            return None
        else:
            full_collection_name = f"{collection_name}_{language}"
            return Chroma(
                collection_name=full_collection_name,
                persist_directory="./.chroma",
                embedding_function=embeddings,
            ).as_retriever()
    except Exception as e:
        print(f"Error getting retriever for {collection_name} in {language}: {e}")
        return None
