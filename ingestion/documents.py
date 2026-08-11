"""Shared helpers for building and ingesting LangChain Documents."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingestion.chub_client import parse_frontmatter
from ingestion.namespace_map import namespace_for_doc_id

logger = logging.getLogger(__name__)


def build_firecrawl_document(
    content: str,
    url: str,
    framework: str,
) -> Document:
    return Document(
        page_content=content,
        metadata={
            "source": url,
            "origin": "firecrawl",
            "framework": framework,
            "title": url.rstrip("/").split("/")[-1] or url,
        },
    )


def build_chub_document(
    markdown: str,
    doc_id: str,
    *,
    language: Optional[str] = None,
    namespace: Optional[str] = None,
) -> Document:
    """Build a Document from chub markdown, prepending identity for chunking."""
    frontmatter, body = parse_frontmatter(markdown)
    meta_block = frontmatter.get("metadata") or {}
    if not isinstance(meta_block, dict):
        meta_block = {}

    title = frontmatter.get("name") or doc_id
    description = frontmatter.get("description") or ""
    version = meta_block.get("versions") or frontmatter.get("version") or ""
    langs = meta_block.get("languages") or language or ""
    if isinstance(langs, list):
        langs = ",".join(str(x) for x in langs)

    ns = namespace or namespace_for_doc_id(doc_id)

    header_parts = [f"# {title}", f"Doc ID: {doc_id}"]
    if description:
        header_parts.append(description)
    if version:
        header_parts.append(f"Version: {version}")
    if langs:
        header_parts.append(f"Language: {langs}")
    page_content = "\n\n".join(header_parts) + "\n\n" + body

    return Document(
        page_content=page_content,
        metadata={
            "source": doc_id,
            "origin": "chub",
            "framework": ns,
            "doc_id": doc_id,
            "language": str(langs) if langs else (language or ""),
            "version": str(version) if version else "",
            "title": str(title),
        },
    )


def ingest_documents(
    framework: str,
    docs_list: list[Document],
    *,
    # Under e5's 512 limit; tiktoken undercounts vs the embedding tokenizer.
    chunk_size: int = 400,
    chunk_overlap: int = 40,
) -> bool:
    """Chunk documents and add them to the vector store namespace."""
    from agent.graph.models.embeddings import embeddings
    from agent.graph.vector_stores import get_vector_store

    if not docs_list:
        logger.info("No documents to ingest for %s", framework)
        return False

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    doc_splits = text_splitter.split_documents(docs_list)
    if not doc_splits:
        logger.info("No chunks produced for %s", framework)
        return False

    vector_store = get_vector_store(framework, embeddings)
    if not vector_store:
        logger.error("Could not create vector store for %s", framework)
        return False

    logger.info(
        "Adding %d chunks (%d source docs) to namespace %s",
        len(doc_splits),
        len(docs_list),
        framework,
    )
    vector_store.add_documents(doc_splits)

    # App-level catalog: packages successfully indexed under Pinecone `chub`.
    if framework == "chub":
        try:
            from agent.graph.stores import remember_chub_package

            for doc in docs_list:
                doc_id = (doc.metadata or {}).get("doc_id") or (
                    doc.metadata or {}
                ).get("source")
                if not doc_id:
                    continue
                title = (doc.metadata or {}).get("title")
                remember_chub_package(str(doc_id), title)
        except Exception:
            logger.exception(
                "Failed to update chub package catalog after ingest"
            )

    return True


def ingest_by_framework(docs: Iterable[Document]) -> dict[str, int]:
    """Group docs by metadata['framework'] and ingest each namespace."""
    buckets: dict[str, list[Document]] = {}
    for doc in docs:
        fw = doc.metadata.get("framework") or "chub"
        buckets.setdefault(fw, []).append(doc)

    counts: dict[str, int] = {}
    for framework, group in buckets.items():
        ok = ingest_documents(framework, group)
        counts[framework] = len(group) if ok else 0
    return counts
