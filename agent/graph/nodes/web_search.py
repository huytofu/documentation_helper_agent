from typing import Any, Dict

from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults

from agent.graph.state import GraphState

web_search_tool = TavilySearchResults(k=3)

def get_content(doc: Document) -> str:
    if isinstance(doc, Document):
        if doc.metadata.get("source") == "web":
            return doc.page_content[:500]
        else:
            return ""
    else:
        return ""

def web_search(state: GraphState) -> Dict[str, Any]:
    print("---WEB SEARCH---")
    query = state["query"]
    documents = state["documents"]

    docs = web_search_tool.invoke({"query": query})
    web_results = "\n".join([get_content(d) for d in docs[:3]])
    web_results = Document(page_content=web_results)
    if documents is not None:
        documents.append(web_results)
    else:
        documents = [web_results]
    return {"documents": documents, "current_node": "WEB_SEARCH"}
