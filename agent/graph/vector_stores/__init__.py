"""Vector Store Factory

This module provides a factory for creating vector stores based on the deployment environment.
It supports Chroma for local development and Pinecone for serverless deployments.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from langchain_core.vectorstores import VectorStore

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Get the vector store type from environment variable
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chroma").lower()

def get_vector_store(
    collection_name: str,
    embedding_function: any
) -> Optional[VectorStore]:
    """Get the appropriate vector store based on VECTOR_STORE_TYPE environment variable.
    
    Args:
        collection_name: The name of the collection
        embedding_function: The embedding function to use
        
    Returns:
        A vector store instance or None if an error occurs
    """
    try:
        if VECTOR_STORE_TYPE == "chroma":
            from langchain_chroma import Chroma
            
            logger.info(f"Using Chroma vector store with collection: {collection_name}")
            return Chroma(
                collection_name=collection_name,
                persist_directory="./.chroma",
                embedding_function=embedding_function,
            )
            
        elif VECTOR_STORE_TYPE == "pinecone":
            from langchain_pinecone import Pinecone
            from pinecone import Pinecone as PineconeClient
            
            # Get Pinecone credentials from environment variables
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
            pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
            
            # Validate credentials
            if not all([pinecone_api_key, pinecone_environment, pinecone_index_name]):
                raise ValueError(
                    "Pinecone credentials are required. "
                    "Set PINECONE_API_KEY, PINECONE_ENVIRONMENT, and PINECONE_INDEX_NAME environment variables."
                )
            
            # Initialize Pinecone with the new client syntax
            pc = PineconeClient(api_key=pinecone_api_key)
            
            # Get the index
            index = pc.Index(pinecone_index_name)
            
            logger.info(f"Using Pinecone vector store with namespace: {collection_name}")
            return Pinecone(
                index=index,
                embedding=embedding_function,
                namespace=collection_name,
            )
            
        else:
            logger.warning(f"Unknown vector store type: {VECTOR_STORE_TYPE}. Falling back to Chroma.")
            from langchain_chroma import Chroma
            
            return Chroma(
                collection_name=collection_name,
                persist_directory="./.chroma",
                embedding_function=embedding_function,
            )
            
    except Exception as e:
        logger.error(f"Error creating vector store for {collection_name}: {e}")
        return None 