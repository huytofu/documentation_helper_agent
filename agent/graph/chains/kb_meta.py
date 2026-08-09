"""Answer rare questions about what this app's knowledge base contains."""

from langchain_core.prompts import ChatPromptTemplate
from agent.graph.models.kb_meta import llm

system = """You answer questions about THIS APP's documentation knowledge base only.

Static framework namespaces we can retrieve from:
- langgraph
- llamaindex
- smolagents
- copilotkit
- chub (other curated package/SDK docs such as OpenAI, Pinecone, etc.)

Indexed packages currently remembered for the chub namespace:
{kb_catalog}

Rules:
- Answer only from the static list and the chub catalog above.
- List frameworks clearly; list chub packages when present.
- If the chub catalog is "(none indexed yet)" or empty, say no chub packages are remembered yet, but still list the static frameworks.
- Do NOT invent vector counts, ingest dates, index size, backend type, or topics beyond this catalog.
- Do NOT give library how-to tutorials; if asked how to use a library, briefly say you can retrieve docs for that topic instead.
- Keep the reply concise and helpful.
"""

kb_meta_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{query}"),
    ]
)

kb_meta_chain = kb_meta_prompt | llm


def invoke_kb_meta(query: str, kb_catalog: str = "(none indexed yet)") -> str:
    """Generate a catalog-only reply about the app knowledge base."""
    result = kb_meta_chain.invoke(
        {
            "query": query,
            "kb_catalog": kb_catalog or "(none indexed yet)",
        }
    )
    if hasattr(result, "content"):
        return result.content
    return str(result)
