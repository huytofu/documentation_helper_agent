from agent.graph.models.embeddings import embeddings
from agent.graph.vector_stores import get_vector_store


def get_retriever(collection_name):
    """Get a retriever for the specified collection and language.
    
    Args:
        collection_name: The name of the collection
        
    Returns:
        A retriever instance or None if an error occurs
    """
    try:
        # Get the appropriate vector store based on environment
        vector_store = get_vector_store(collection_name, embeddings)
        
        # Return the vector store as a retriever if it exists
        if vector_store:
            return vector_store.as_retriever()
        else:
            return None
            
    except Exception as e:
        print(f"Error getting retriever for {collection_name}: {e}")
        return None
