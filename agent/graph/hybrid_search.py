"""Placeholder hybrid search for a future RETRIEVE enhancement.

Not wired into the graph yet. Intended to replace the current single-namespace
pure-vector call in agent/graph/nodes/retrieve.py with fused ranking across
one or more Pinecone namespaces.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Must stay in sync with agent/graph/chains/vectorstore_router.py
KNOWN_FRAMEWORKS = [
    "langgraph",
    "copilotkit",
    "chub",
    "others",
]


def hybrid_documentation_search(
    query: str,
    frameworks: List[str],
    limit: int = 5,
    keyword_weight: float = 0.3,
) -> Dict[str, Any]:
    """Perform hybrid (vector + keyword) search across frameworks.

    Placeholder: returns an empty result payload shaped for the future
    RETRIEVE integration. Real logic should combine
    ``agent.graph.retrievers.get_retriever`` with a keyword index and fuse
    scores (RRF or weighted sum via ``keyword_weight``).

    Args:
        query: Search query.
        frameworks: Namespaces to search (subset of KNOWN_FRAMEWORKS).
        limit: Max results per framework (default 5).
        keyword_weight: Fusion weight for keyword score in [0, 1]
            (0 = pure vector, 1 = pure keyword).

    Returns:
        Dict with query, frameworks, results list, and placeholder=True.
    """
    unknown = [f for f in frameworks if f not in KNOWN_FRAMEWORKS]
    return {
        "query": query,
        "frameworks": frameworks,
        "unknown_frameworks": unknown,
        "limit": limit,
        "keyword_weight": keyword_weight,
        "results": [],
        "placeholder": True,
    }
