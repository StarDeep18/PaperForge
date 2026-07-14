"""
Vector Store Interface.

Abstract base class for vector database operations.
Designed to be swappable between ChromaDB, Qdrant, Pinecone, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.chunk import Chunk, SearchResult
from app.domain.entities.vector_store_result import VectorSearchResult, VectorStoreResult


class VectorStore(ABC):
    """
    Abstract interface for vector storage and retrieval.

    This abstraction allows swapping the vector database
    implementation without changing any business logic.
    """

    @abstractmethod
    async def add_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        """
        Store document chunks with their embeddings.

        Args:
            chunks: List of Chunk entities with embeddings populated.
        """
        pass

    @abstractmethod
    async def update_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        """
        Update existing document chunks and their embeddings.

        Args:
            chunks: List of Chunk entities to update.
        """
        pass

    @abstractmethod
    async def delete_chunks(self, chunk_ids: list[str]) -> VectorStoreResult:
        """
        Remove specific chunks by their IDs.

        Args:
            chunk_ids: List of chunk IDs to delete.
        """
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> VectorStoreResult:
        """
        Remove all chunks belonging to a document.

        Args:
            document_id: The ID of the document to delete.
        """
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: float = 0.3,
    ) -> list[VectorSearchResult]:
        """
        Perform similarity search against stored chunks.

        Args:
            query_embedding: The embedded query vector.
            top_k: Maximum number of results to return.
            filter_document_ids: Optional list of document IDs to scope search.
            filter_collection_id: Optional collection ID to scope search.
            score_threshold: Minimum similarity score to include.

        Returns:
            List of VectorSearchResult ordered by relevance.
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Check the status of the vector database.

        Returns:
            Dict containing status, provider, collection counts, etc.
        """
        pass

    @abstractmethod
    async def count(self, document_id: Optional[str] = None) -> int:
        """Count stored chunks, optionally filtered by document."""
        pass

    # ── Backward Compatibility API ────────────────────────────────
    # Supports the previous VectorStore API used by RAGChain.

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        """Bridge method for existing RAGChain similarity search."""
        results = await self.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_document_ids=filter_document_ids,
            filter_collection_id=filter_collection_id,
            score_threshold=score_threshold,
        )
        
        legacy_results = []
        for r in results:
            legacy_results.append(
                SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.chunk.content,
                    parent_content=r.chunk.parent_content,
                    page_number=r.chunk.page_number,
                    section_header=r.chunk.section_header,
                    score=r.similarity_score,
                    metadata=r.metadata,
                )
            )
        return legacy_results

    async def delete_by_document(self, document_id: str) -> None:
        """Bridge method for deleting chunks belonging to a document."""
        await self.delete_document(document_id)

    async def delete_by_collection(self, collection_id: str) -> None:
        """Bridge method for deleting chunks belonging to a collection."""
        # ChromaDB implementation deletes using metadata filters
        # To maintain compatibility we keep this as a dummy/legacy call 
        # or implement it via delete_chunks.
        pass
