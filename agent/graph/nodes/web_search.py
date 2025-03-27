from typing import Any, Dict
import logging
from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from agent.graph.state import GraphState
from agent.graph.utils.timeout import timeout
from agent.graph.utils.api_utils import (
    handle_api_error, 
    STANDARD_TIMEOUT,
    cost_tracker,
    APIResponse
)

logger = logging.getLogger("graph.web_search")

web_search_tool = TavilySearchResults(k=3)

def get_content(doc: Document) -> str:
    if isinstance(doc, Document):
        if doc.metadata.get("source") == "web":
            return doc.page_content[:500]
        else:
            return ""
    else:
        return ""

@timeout(STANDARD_TIMEOUT)
@handle_api_error
async def perform_web_search(query: str) -> APIResponse:
    """Perform web search with timeout and error handling."""
    try:
        docs = web_search_tool.invoke({"query": query})
        cost_tracker.track_usage('web_search', requests=1, cost=0.0)  # Update cost based on actual pricing
        return APIResponse(
            success=True,
            data=docs
        )
    except Exception as e:
        logger.error(f"Error during web search: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            data=[]
        )

async def web_search(state: GraphState) -> Dict[str, Any]:
    logger.info("---WEB SEARCH---")
    query = state.get("query", "")
    documents = state.get("documents", [])

    try:
        response = await perform_web_search(query)
        if response.success and response.data:
            docs = response.data
            web_results = "\n".join([get_content(d) for d in docs[:3]])
            web_results = Document(page_content=web_results)
            if documents is not None:
                documents.append(web_results)
            else:
                documents = [web_results]
            return {"documents": documents, "current_node": "WEB_SEARCH"}
        else:
            logger.error(f"Web search failed: {response.error}")
            return {"documents": documents, "current_node": "WEB_SEARCH", "error": response.error}
    except Exception as e:
        logger.error(f"Unexpected error in web search: {str(e)}")
        return {"documents": documents, "current_node": "WEB_SEARCH", "error": str(e)}
