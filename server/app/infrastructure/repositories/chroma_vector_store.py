"""
ChromaDB Vector Store Implementation.

Concrete implementation of the VectorStore interface using ChromaDB.
Stores document chunk embeddings for semantic retrieval.
"""

import time
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.vector_store_result import VectorSearchResult, VectorStoreResult
from app.domain.repositories.vector_store import VectorStore
from app.domain.exceptions import (
    ConnectionFailure,
    VectorInsertError,
    VectorSearchError,
    VectorDeleteError,
)


class ChromaVectorStore(VectorStore):
    """
    ChromaDB-based vector store implementation.

    Uses ChromaDB's persistent client for durable storage.
    All chunks are stored in a single collection with metadata
    filters for document-level and collection-level scoping.
    """

    def __init__(self):
        settings = get_settings()
        try:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            
            # Use distance metric from settings (ChromaDB uses metadata space config)
            space_metric = settings.vector_store_distance_metric
            # map distance metric names if necessary
            # hnsw:space supports "l2", "ip", or "cosine"
            if space_metric not in ("l2", "ip", "cosine"):
                space_metric = "cosine"
                
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": space_metric},
            )
            logger.info(
                f"ChromaDB initialized: collection='{settings.chroma_collection_name}', "
                f"space='{space_metric}', count={self._collection.count()}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise ConnectionFailure("chromadb", str(e)) from e

    async def add_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        start_time = time.perf_counter()
        if not chunks:
            return VectorStoreResult(
                success=True, operation="insert", processed_count=0, duration=0.0
            )

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
        metadatas = [chunk.retrieval_metadata for chunk in chunks]

        try:
            # ChromaDB batch upsert
            self._collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            duration = (time.perf_counter() - start_time) * 1000.0
            return VectorStoreResult(
                success=True,
                operation="insert",
                processed_count=len(chunks),
                duration=duration,
            )
        except Exception as e:
            raise VectorInsertError(f"ChromaDB upsert failure: {e}") from e

    async def update_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        start_time = time.perf_counter()
        if not chunks:
            return VectorStoreResult(
                success=True, operation="update", processed_count=0, duration=0.0
            )

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
        metadatas = [chunk.retrieval_metadata for chunk in chunks]

        try:
            self._collection.update(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            duration = (time.perf_counter() - start_time) * 1000.0
            return VectorStoreResult(
                success=True,
                operation="update",
                processed_count=len(chunks),
                duration=duration,
            )
        except Exception as e:
            raise VectorInsertError(f"ChromaDB update failure: {e}") from e

    async def delete_chunks(self, chunk_ids: list[str]) -> VectorStoreResult:
        start_time = time.perf_counter()
        if not chunk_ids:
            return VectorStoreResult(
                success=True, operation="delete_chunks", processed_count=0, duration=0.0
            )

        try:
            self._collection.delete(ids=chunk_ids)
            duration = (time.perf_counter() - start_time) * 1000.0
            return VectorStoreResult(
                success=True,
                operation="delete_chunks",
                processed_count=len(chunk_ids),
                duration=duration,
            )
        except Exception as e:
            raise VectorDeleteError(f"ChromaDB delete failure: {e}") from e

    async def delete_document(self, document_id: str) -> VectorStoreResult:
        start_time = time.perf_counter()
        try:
            # Retrieve counts before deleting to populate statistics
            count_before = await self.count(document_id)
            
            self._collection.delete(where={"document_id": document_id})
            duration = (time.perf_counter() - start_time) * 1000.0
            return VectorStoreResult(
                success=True,
                operation="delete_document",
                processed_count=count_before,
                duration=duration,
            )
        except Exception as e:
            raise VectorDeleteError(f"ChromaDB document deletion failure for '{document_id}': {e}") from e

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: float = 0.3,
    ) -> list[VectorSearchResult]:
        start_time = time.perf_counter()
        where_filter = None

        # Build filters dictionary
        filters = []
        if filter_document_ids:
            if len(filter_document_ids) == 1:
                filters.append({"document_id": filter_document_ids[0]})
            else:
                filters.append(
                    {"$or": [{"document_id": doc_id} for doc_id in filter_document_ids]}
                )

        if filter_collection_id:
            filters.append({"collection_id": filter_collection_id})

        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"$and": filters}

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            raise VectorSearchError(f"ChromaDB query search failure: {e}") from e

        search_results: list[VectorSearchResult] = []

        if not results or not results["ids"] or not results["ids"][0]:
            return search_results

        retrieval_time = time.perf_counter() - start_time

        for i, chunk_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 1.0
            score = 1.0 - distance  # Convert cosine distance to similarity score

            if score < score_threshold:
                continue

            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            content = results["documents"][0][i] if results["documents"] else ""

            chunk = Chunk(
                id=chunk_id,
                document_id=metadata.get("document_id", ""),
                content=content,
                parent_content=metadata.get("parent_content"),
                parent_chunk_id=metadata.get("parent_chunk_id"),
                page_number=metadata.get("page_number"),
                section_header=metadata.get("section_header"),
                chunk_index=metadata.get("chunk_index", 0),
                total_chunks=metadata.get("total_chunks", 0),
                character_start=metadata.get("character_start", 0),
                character_end=metadata.get("character_end", 0),
                embedding=None,
                metadata=metadata,
            )

            search_results.append(
                VectorSearchResult(
                    chunk=chunk,
                    similarity_score=score,
                    document_id=chunk.document_id,
                    chunk_id=chunk_id,
                    metadata=metadata,
                    provider="chromadb",
                    retrieval_time=retrieval_time,
                )
            )

        return sorted(search_results, key=lambda r: r.similarity_score, reverse=True)

    async def health_check(self) -> dict:
        try:
            # Query diagnostics
            col_list = self._client.list_collections()
            collection_count = len(col_list)
            doc_count = self._collection.count()
            
            db_version = "unknown"
            try:
                if hasattr(self._client, "get_version"):
                    db_version = self._client.get_version()
            except Exception:
                pass

            return {
                "provider": "chromadb",
                "status": "healthy",
                "collection_count": collection_count,
                "document_count": doc_count,
                "embedding_dimension": get_settings().embedding_dimension,
                "database_version": db_version,
            }
        except Exception as e:
            raise ConnectionFailure("chromadb", str(e)) from e

    async def count(self, document_id: Optional[str] = None) -> int:
        try:
            if document_id:
                results = self._collection.get(
                    where={"document_id": document_id},
                    include=[],
                )
                return len(results["ids"]) if results["ids"] else 0
            return self._collection.count()
        except Exception as e:
            raise VectorSearchError(f"ChromaDB count retrieval failure: {e}") from e
