from typing import Any, Dict
import logging
from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from agent.graph.state import GraphState
from agent.graph.utils.timeout import timeout

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

@timeout(30)  # 30 second timeout for web search
def perform_web_search(query: str) -> list[Document]:
    """Perform web search with timeout"""
    return web_search_tool.invoke({"query": query})

def web_search(state: GraphState) -> Dict[str, Any]:
    logger.info("---WEB SEARCH---")
    query = state.get("query", "")
    documents = state.get("documents", [])

    try:
        docs = perform_web_search(query)
        web_results = "\n".join([get_content(d) for d in docs[:3]])
        web_results = Document(page_content=web_results)
        if documents is not None:
            documents.append(web_results)
        else:
            documents = [web_results]
        return {"documents": documents, "current_node": "WEB_SEARCH"}
    except TimeoutError:
        logger.error("Web search timed out")
        return {"documents": documents, "current_node": "WEB_SEARCH", "error": "Web search timed out"}
    except Exception as e:
        logger.error(f"Error during web search: {str(e)}")
        return {"documents": documents, "current_node": "WEB_SEARCH", "error": str(e)}
