from typing import Any, Dict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from agent.graph.chains.retrieval_grader import grade_single_document
from agent.graph.state import GraphState
from agent.graph.utils.message_utils import get_page_content
from agent.graph.utils.api_utils import (
    handle_api_error,
    GRADER_TIMEOUT,
    cost_tracker,
    APIResponse,
    GradingResponse
)
import asyncio
from functools import partial
from copilotkit.langgraph import copilotkit_emit_state

logger = logging.getLogger("graph.grade_documents")

async def grade_documents(state: GraphState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Determines whether the retrieved documents are relevant to the query using parallel processing
    
    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Filtered out irrelevant documents
    """
    logger.info("---CHECK DOCUMENT RELEVANCE TO QUERY---")
    if config:
        generating_state = {
            "current_node": "GRADE_DOCUMENTS",
        }
        print(f"Emitting generating state: {generating_state}")
        await copilotkit_emit_state(config, generating_state)

    query = state.get("query", "")
    documents = state.get("documents", [])
    
    if not documents:
        logger.info("---NO DOCUMENTS TO GRADE---")
        return {"documents": [], "query": query, "current_node": "GRADE_DOCUMENTS"}

    filtered_docs = []
    errors = []
    
    @handle_api_error
    def process_document(doc):
        try:
            score = grade_single_document(
                query=query,
                document=get_page_content(doc)
            )
            # Track API usage
            cost_tracker.track_usage(
                'grader',
                tokens=len(get_page_content(doc).split()),  # Approximate token count
                cost=0.0  # Update cost based on actual pricing
            )
            return GradingResponse(
                success=True,
                doc=doc,
                score=score,
                error=None
            )
        except TimeoutError:
            return GradingResponse(
                success=False,
                doc=doc,
                score=None,
                error="timeout"
            )
        except Exception as e:
            return GradingResponse(
                success=False,
                doc=doc,
                score=None,
                error=str(e)
            )

    # Use ThreadPoolExecutor for parallel processing with max workers
    max_workers = min(len(documents), 3)  # Limit concurrent workers
    overall_timeout = GRADER_TIMEOUT * max_workers  # Scale timeout with number of workers
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all grading tasks
            future_to_doc = {
                executor.submit(process_document, doc): doc 
                for doc in documents
            }
            
            # Process completed tasks with overall timeout
            for future in as_completed(future_to_doc, timeout=overall_timeout):
                doc = future_to_doc[future]
                try:
                    result = future.result(timeout=GRADER_TIMEOUT)
                    if result.success:
                        if result.score and result.score.binary_score.lower() == "yes":
                            logger.info("---GRADE: DOCUMENT RELEVANT---")
                            filtered_docs.append(result.doc)
                        else:
                            logger.info("---GRADE: DOCUMENT NOT RELEVANT---")
                    else:
                        if result.error == "timeout":
                            logger.error(f"Document grading timed out for document: {doc}")
                        else:
                            logger.error(f"Error grading document: {result.error}")
                        errors.append(result.error)
                except TimeoutError:
                    logger.error(f"Individual document grading timed out: {doc}")
                    errors.append("timeout")
                except Exception as e:
                    logger.error(f"Unexpected error processing document: {str(e)}")
                    errors.append(str(e))
    except TimeoutError:
        logger.error("Overall document grading process timed out")
        errors.append("overall_timeout")
    except Exception as e:
        logger.error(f"Unexpected error in document grading process: {str(e)}")
        errors.append(str(e))

    if errors:
        logger.warning(f"Encountered {len(errors)} errors during document grading")
    
    return {
        "documents": filtered_docs,
        "query": query,
        "errors": errors if errors else None
    }
