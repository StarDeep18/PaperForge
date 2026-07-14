"""
ChromaDB Vector Store Implementation.

Concrete implementation of the VectorStore interface using ChromaDB.
Stores document chunk embeddings for semantic retrieval.
"""

from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.chunk import Chunk, SearchResult
from app.domain.repositories.vector_store import VectorStore


class ChromaVectorStore(VectorStore):
    """
    ChromaDB-based vector store implementation.

    Uses ChromaDB's persistent client for durable storage.
    All chunks are stored in a single collection with metadata
    filters for document-level and collection-level scoping.
    """

    def __init__(self):
        settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB initialized: collection='{settings.chroma_collection_name}', "
            f"count={self._collection.count()}"
        )

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
        metadatas = [chunk.retrieval_metadata for chunk in chunks]

        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Expected {len(chunks)} embeddings, got {len(embeddings)}. "
                "All chunks must have embeddings before storage."
            )

        # ChromaDB batch upsert
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks in ChromaDB")

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        where_filter = None

        if filter_document_ids:
            if len(filter_document_ids) == 1:
                where_filter = {"document_id": filter_document_ids[0]}
            else:
                where_filter = {
                    "$or": [
                        {"document_id": doc_id} for doc_id in filter_document_ids
                    ]
                }

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return []

        search_results: list[SearchResult] = []

        if not results or not results["ids"] or not results["ids"][0]:
            return search_results

        for i, chunk_id in enumerate(results["ids"][0]):
            # ChromaDB returns cosine distance; convert to similarity score
            distance = results["distances"][0][i] if results["distances"] else 1.0
            score = 1.0 - distance  # cosine similarity

            if score < score_threshold:
                continue

            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            content = results["documents"][0][i] if results["documents"] else ""

            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=metadata.get("document_id", ""),
                    content=content,
                    page_number=metadata.get("page_number"),
                    section_header=metadata.get("section_header"),
                    score=score,
                    metadata=metadata,
                )
            )

        return sorted(search_results, key=lambda r: r.score, reverse=True)

    async def delete_by_document(self, document_id: str) -> None:
        try:
            self._collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted chunks for document {document_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}")

    async def delete_by_collection(self, collection_id: str) -> None:
        try:
            self._collection.delete(where={"collection_id": collection_id})
            logger.info(f"Deleted chunks for collection {collection_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for collection {collection_id}: {e}")

    async def count(self, document_id: Optional[str] = None) -> int:
        if document_id:
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )
            return len(results["ids"]) if results["ids"] else 0
        return self._collection.count()
