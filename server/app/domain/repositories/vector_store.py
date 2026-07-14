"""
Vector Store Interface.

Abstract base class for vector database operations.
Designed to be swappable between ChromaDB, Qdrant, Pinecone, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.chunk import Chunk, SearchResult


class VectorStore(ABC):
    """
    Abstract interface for vector storage and retrieval.

    This abstraction allows swapping the vector database
    implementation without changing any business logic.
    """

    @abstractmethod
    async def add_chunks(self, chunks: list[Chunk]) -> None:
        """
        Store document chunks with their embeddings.

        Args:
            chunks: List of Chunk entities with embeddings populated.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        """
        Perform similarity search against stored chunks.

        Args:
            query_embedding: The embedded query vector.
            top_k: Maximum number of results to return.
            filter_document_ids: Optional list of document IDs to scope search.
            filter_collection_id: Optional collection ID to scope search.
            score_threshold: Minimum similarity score to include.

        Returns:
            List of SearchResult ordered by relevance (highest first).
        """
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> None:
        """Remove all chunks belonging to a document."""
        ...

    @abstractmethod
    async def delete_by_collection(self, collection_id: str) -> None:
        """Remove all chunks belonging to documents in a collection."""
        ...

    @abstractmethod
    async def count(self, document_id: Optional[str] = None) -> int:
        """Count stored chunks, optionally filtered by document."""
        ...
