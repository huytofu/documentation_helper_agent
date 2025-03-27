from typing import Any, Dict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.graph.chains.retrieval_grader import grade_single_document
from agent.graph.state import GraphState
from agent.graph.utils.message_utils import get_page_content
from concurrent.futures import TimeoutError

logger = logging.getLogger("graph.grade_documents")

def grade_documents(state: GraphState) -> Dict[str, Any]:
    """
    Determines whether the retrieved documents are relevant to the query using parallel processing
    
    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Filtered out irrelevant documents
    """
    logger.info("---CHECK DOCUMENT RELEVANCE TO QUERY---")
    query = state.get("query", "")
    documents = state.get("documents", [])
    
    if not documents:
        logger.info("---NO DOCUMENTS TO GRADE---")
        return {"documents": [], "query": query, "current_node": "GRADE_DOCUMENTS"}

    filtered_docs = []
    errors = []
    
    def process_document(doc):
        try:
            score = grade_single_document(
                query=query,
                document=get_page_content(doc)
            )
            return {
                "success": True,
                "doc": doc,
                "score": score,
                "error": None
            }
        except TimeoutError:
            return {
                "success": False,
                "doc": doc,
                "score": None,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "doc": doc,
                "score": None,
                "error": str(e)
            }

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all grading tasks
        future_to_doc = {
            executor.submit(process_document, doc): doc 
            for doc in documents
        }
        
        # Process completed tasks
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                result = future.result()
                if result["success"]:
                    if result["score"].binary_score.lower() == "yes":
                        logger.info("---GRADE: DOCUMENT RELEVANT---")
                        filtered_docs.append(result["doc"])
                    else:
                        logger.info("---GRADE: DOCUMENT NOT RELEVANT---")
                else:
                    if result["error"] == "timeout":
                        logger.error(f"Document grading timed out for document: {doc}")
                    else:
                        logger.error(f"Error grading document: {result['error']}")
                    errors.append(result["error"])
            except Exception as e:
                logger.error(f"Unexpected error processing document: {str(e)}")
                errors.append(str(e))

    if errors:
        logger.warning(f"Encountered {len(errors)} errors during document grading")
    
    return {
        "documents": filtered_docs,
        "query": query,
        "current_node": "GRADE_DOCUMENTS",
        "errors": errors if errors else None
    }
