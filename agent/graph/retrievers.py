from agent.graph.models.embeddings import embeddings
from agent.graph.vector_stores import get_vector_store

# High enough to cover one chub source document's chunks (no artificial cap).
_DIRECT_DUMP_K = 10_000


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


def _doc_sort_key(doc) -> tuple:
    meta = getattr(doc, "metadata", None) or {}
    chunk_id = (
        meta.get("id")
        or getattr(doc, "id", None)
        or meta.get("chunk_id")
        or ""
    )
    return (str(chunk_id), (getattr(doc, "page_content", None) or "")[:80])


def get_documents_by_doc_id(collection_name: str, doc_id: str) -> list:
    """Fetch all chunks for a chub doc_id via metadata filter (browse/dump path).

    Prefer filter-constrained fetch over query ranking. Sorted deterministically
    by available chunk id / content prefix. No artificial result cap.
    """
    if not collection_name or not doc_id:
        return []
    try:
        vector_store = get_vector_store(collection_name, embeddings)
        if vector_store is None:
            return []

        filter_eq = {"doc_id": {"$eq": doc_id}}
        docs = []
        try:
            docs = vector_store.similarity_search(
                doc_id, k=_DIRECT_DUMP_K, filter=filter_eq
            )
        except Exception:
            # Some backends accept bare equality maps.
            docs = vector_store.similarity_search(
                doc_id, k=_DIRECT_DUMP_K, filter={"doc_id": doc_id}
            )

        if not docs:
            # Ingest also sets metadata.source = doc_id for chub docs.
            try:
                docs = vector_store.similarity_search(
                    doc_id,
                    k=_DIRECT_DUMP_K,
                    filter={"source": {"$eq": doc_id}},
                )
            except Exception:
                docs = vector_store.similarity_search(
                    doc_id, k=_DIRECT_DUMP_K, filter={"source": doc_id}
                )

        return sorted(docs or [], key=_doc_sort_key)
    except Exception as e:
        print(f"Error dumping documents for {collection_name}/{doc_id}: {e}")
        return []
