"""
Vector Store Service.

Domain service that orchestrates storage, validation, batching, and search
operations on the vector database.
"""

import math
import time
from typing import Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.vector_store_result import VectorSearchResult, VectorStoreResult
from app.domain.repositories.vector_store import VectorStore
from app.domain.exceptions import (
    VectorStoreError,
    DuplicateChunk,
    VectorInsertError,
    VectorSearchError,
    VectorDeleteError,
)


class VectorStoreService:
    """
    Business orchestration service for vector database operations.
    
    Provides validation of vectors, batch write orchestration, search metrics,
    and structured logging.
    """

    def __init__(self, vector_store: VectorStore):
        self._vector_store = vector_store

    def _validate_chunks_for_insert(self, chunks: list[Chunk], expected_dim: int) -> None:
        """Validate list of chunks before writing to database."""
        seen_ids = set()
        for chunk in chunks:
            # 1. Duplicate chunk IDs check in the input batch
            if chunk.id in seen_ids:
                raise DuplicateChunk(chunk.id)
            seen_ids.add(chunk.id)
            
            # 2. Empty vectors check
            if not chunk.embedding:
                raise VectorInsertError(f"Chunk '{chunk.id}' contains an empty or null embedding vector.")
                
            # 3. Embedding dimension check
            actual_dim = len(chunk.embedding)
            if actual_dim != expected_dim:
                raise VectorInsertError(
                    f"Chunk '{chunk.id}' embedding dimension {actual_dim} does not match expected {expected_dim}."
                )
                
            # 4. NaN / infinite values check
            if any(math.isnan(x) or not math.isfinite(x) for x in chunk.embedding):
                raise VectorInsertError(f"Chunk '{chunk.id}' embedding contains NaN or infinite values.")
                
            # 5. Metadata dictionary check
            if not isinstance(chunk.metadata, dict):
                raise VectorInsertError(f"Chunk '{chunk.id}' metadata must be a dictionary.")

    async def add_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        """
        Validate, batch, and store embedded chunks into the vector store.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        
        if not chunks:
            return VectorStoreResult(
                success=True,
                operation="insert",
                processed_count=0,
                duration=0.0,
                warnings=["Received empty list of chunks to insert."]
            )

        try:
            # Perform validations
            self._validate_chunks_for_insert(chunks, settings.embedding_dimension)
            
            # Partition into batches
            batch_size = settings.vector_store_batch_size
            batches = [
                chunks[i : i + batch_size]
                for i in range(0, len(chunks), batch_size)
            ]
            
            processed_count = 0
            for batch in batches:
                # Add to DB
                await self._vector_store.add_chunks(batch)
                processed_count += len(batch)
                
            duration = (time.perf_counter() - start_time) * 1000.0
            
            # Structured logging
            logger.info(
                f"Vector store insert completed: collection='{settings.chroma_collection_name}', "
                f"operation='insert', chunk_count={processed_count}, duration={duration:.1f}ms, "
                f"errors=0, warnings=0"
            )
            
            return VectorStoreResult(
                success=True,
                operation="insert",
                processed_count=processed_count,
                duration=duration,
                warnings=[]
            )
            
        except VectorStoreError as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store insert failed: collection='{settings.chroma_collection_name}', "
                f"operation='insert', chunk_count={len(chunks)}, duration={duration:.1f}ms, "
                f"error='{str(e)}'"
            )
            raise
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store insert failed with unexpected error: collection='{settings.chroma_collection_name}', "
                f"operation='insert', chunk_count={len(chunks)}, duration={duration:.1f}ms, "
                f"error='{str(e)}'"
            )
            raise VectorInsertError(str(e)) from e

    async def update_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        """
        Validate and update existing chunks in the vector store.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        
        if not chunks:
            return VectorStoreResult(
                success=True,
                operation="update",
                processed_count=0,
                duration=0.0,
                warnings=["Received empty list of chunks to update."]
            )

        try:
            self._validate_chunks_for_insert(chunks, settings.embedding_dimension)
            
            batch_size = settings.vector_store_batch_size
            batches = [
                chunks[i : i + batch_size]
                for i in range(0, len(chunks), batch_size)
            ]
            
            processed_count = 0
            for batch in batches:
                await self._vector_store.update_chunks(batch)
                processed_count += len(batch)
                
            duration = (time.perf_counter() - start_time) * 1000.0
            
            logger.info(
                f"Vector store update completed: collection='{settings.chroma_collection_name}', "
                f"operation='update', chunk_count={processed_count}, duration={duration:.1f}ms, "
                f"errors=0, warnings=0"
            )
            
            return VectorStoreResult(
                success=True,
                operation="update",
                processed_count=processed_count,
                duration=duration,
                warnings=[]
            )
            
        except VectorStoreError as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store update failed: collection='{settings.chroma_collection_name}', "
                f"operation='update', chunk_count={len(chunks)}, duration={duration:.1f}ms, "
                f"error='{str(e)}'"
            )
            raise
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            raise VectorInsertError(f"Unexpected update failure: {e}") from e

    async def delete_chunks(self, chunk_ids: list[str]) -> VectorStoreResult:
        """
        Batch delete specific chunks by ID.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        
        if not chunk_ids:
            return VectorStoreResult(
                success=True,
                operation="delete_chunks",
                processed_count=0,
                duration=0.0,
                warnings=["Received empty list of chunk IDs to delete."]
            )

        try:
            batch_size = settings.vector_store_batch_size
            batches = [
                chunk_ids[i : i + batch_size]
                for i in range(0, len(chunk_ids), batch_size)
            ]
            
            processed_count = 0
            for batch in batches:
                await self._vector_store.delete_chunks(batch)
                processed_count += len(batch)
                
            duration = (time.perf_counter() - start_time) * 1000.0
            
            logger.info(
                f"Vector store delete_chunks completed: collection='{settings.chroma_collection_name}', "
                f"operation='delete_chunks', chunk_count={processed_count}, duration={duration:.1f}ms, "
                f"errors=0, warnings=0"
            )
            
            return VectorStoreResult(
                success=True,
                operation="delete_chunks",
                processed_count=processed_count,
                duration=duration,
                warnings=[]
            )
            
        except VectorStoreError as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store delete_chunks failed: collection='{settings.chroma_collection_name}', "
                f"operation='delete_chunks', chunk_count={len(chunk_ids)}, duration={duration:.1f}ms, "
                f"error='{str(e)}'"
            )
            raise
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            raise VectorDeleteError(f"Unexpected delete failure: {e}") from e

    async def delete_document(self, document_id: str) -> VectorStoreResult:
        """
        Delete all chunks associated with a document ID.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        
        if not document_id:
            raise VectorDeleteError("Document ID cannot be empty.")

        try:
            res = await self._vector_store.delete_document(document_id)
            duration = (time.perf_counter() - start_time) * 1000.0
            
            logger.info(
                f"Vector store delete_document completed: collection='{settings.chroma_collection_name}', "
                f"operation='delete_document', document_id='{document_id}', duration={duration:.1f}ms, "
                f"errors=0, warnings=0"
            )
            return res
        except VectorStoreError as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store delete_document failed: collection='{settings.chroma_collection_name}', "
                f"operation='delete_document', document_id='{document_id}', duration={duration:.1f}ms, "
                f"error='{str(e)}'"
            )
            raise
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            raise VectorDeleteError(f"Unexpected delete document failure: {e}") from e

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: Optional[int] = None,
        filter_document_ids: Optional[list[str]] = None,
        filter_collection_id: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> list[VectorSearchResult]:
        """
        Perform similarities search with query checks and threshold filtering.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        
        # 1. Validation
        if not query_embedding:
            raise VectorSearchError("Query embedding vector cannot be empty.")
            
        expected_dim = settings.embedding_dimension
        if len(query_embedding) != expected_dim:
            raise VectorSearchError(
                f"Query embedding dimension {len(query_embedding)} does not match expected {expected_dim}."
            )
            
        if any(math.isnan(x) or not math.isfinite(x) for x in query_embedding):
            raise VectorSearchError("Query embedding contains NaN or infinite values.")

        # Default parameters
        search_top_k = top_k or settings.vector_store_top_k_default
        search_threshold = score_threshold if score_threshold is not None else settings.similarity_threshold
        
        if search_threshold < 0.0 or search_threshold > 1.0:
            raise VectorSearchError(f"Similarity score threshold must be between 0.0 and 1.0. Got {search_threshold}.")

        try:
            results = await self._vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=search_top_k,
                filter_document_ids=filter_document_ids,
                filter_collection_id=filter_collection_id,
                score_threshold=search_threshold,
            )
            
            retrieval_time = time.perf_counter() - start_time
            
            # Populate retrieval time for results
            for res in results:
                res.retrieval_time = retrieval_time

            duration = retrieval_time * 1000.0
            logger.info(
                f"Vector store search completed: collection='{settings.chroma_collection_name}', "
                f"operation='search', results={len(results)}, duration={duration:.1f}ms"
            )
            return results
            
        except VectorStoreError as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store search failed: collection='{settings.chroma_collection_name}', "
                f"operation='search', duration={duration:.1f}ms, error='{str(e)}'"
            )
            raise
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Vector store search failed with unexpected error: collection='{settings.chroma_collection_name}', "
                f"operation='search', duration={duration:.1f}ms, error='{str(e)}'"
            )
            raise VectorSearchError(str(e)) from e

    async def health_check(self) -> dict:
        """
        Obtain health check diagnostics.
        """
        try:
            return await self._vector_store.health_check()
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {
                "provider": "unknown",
                "status": "unhealthy",
                "error": str(e)
            }
