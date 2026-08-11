"""Map chub doc IDs to Pinecone namespaces."""

from __future__ import annotations

# Prefix / exact-id rules evaluated in order (first match wins).
# Framework-specific docs land in existing namespaces; everything else → chub.
_NAMESPACE_RULES: list[tuple[str, str]] = [
    ("langgraph/", "langgraph"),
    ("copilotkit/", "copilotkit"),
]

DEFAULT_CHUB_NAMESPACE = "chub"

# Explicit seed overrides (optional extras beyond prefix rules)
DOC_ID_OVERRIDES: dict[str, str] = {
    "langgraph/package": "langgraph",
    "copilotkit/package": "copilotkit",
}


def namespace_for_doc_id(doc_id: str) -> str:
    """Return the Pinecone namespace for a chub doc id."""
    if doc_id in DOC_ID_OVERRIDES:
        return DOC_ID_OVERRIDES[doc_id]
    for prefix, namespace in _NAMESPACE_RULES:
        if doc_id.startswith(prefix):
            return namespace
    return DEFAULT_CHUB_NAMESPACE


VALID_NAMESPACES = frozenset(
    {
        "langgraph",
        "copilotkit",
        "chub",
    }
)
