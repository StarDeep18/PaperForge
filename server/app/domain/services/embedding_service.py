"""
Embedding Service.

Domain service that orchestrates generating embeddings for document chunks,
validates dimensions, handles batching and concurrency, and returns results.
"""

import asyncio
import time
from typing import Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.chunk import Chunk, ProcessingResult
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.exceptions import EmbeddingError, EmbeddingDimensionMismatch


class EmbeddingService:
    """
    Orchestrator for text chunk embedding generation.
    
    Contains business logic:
    - Partitioning chunks into batches
    - Concurrency limiting
    - Validation of returned embedding dimensions
    - Structured metrics and logging
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        batch_size: Optional[int] = None,
        max_concurrency: Optional[int] = None,
    ):
        self._provider = provider
        settings = get_settings()
        self._batch_size = batch_size or settings.embedding_batch_size
        self._max_concurrency = max_concurrency or settings.embedding_max_concurrency
        self._semaphore = asyncio.Semaphore(self._max_concurrency)

    async def embed_chunks(self, chunks: list[Chunk]) -> ProcessingResult:
        """
        Generate and attach embeddings to a list of Chunk domain entities.

        Args:
            chunks: A list of Chunk objects to embed.

        Returns:
            ProcessingResult containing the updated Chunks and metrics.
            
        Raises:
            EmbeddingError: If API call fails.
            EmbeddingDimensionMismatch: If returned vector sizes don't match the expected dimension.
        """
        start_time = time.perf_counter()
        
        # 1. Handle empty chunks input
        if not chunks:
            logger.info("Embedding service received empty chunk list. Skipping processing.")
            return ProcessingResult(
                success=True,
                duration_ms=0.0,
                warnings=["Received an empty list of chunks."],
                statistics={
                    "total_chunks": 0,
                    "batch_size": self._batch_size,
                    "provider": self._provider.provider_name,
                    "dimension": self._provider.dimension,
                },
                payload=[],
            )

        # 2. Partition chunks into batches
        batches = [
            chunks[i : i + self._batch_size]
            for i in range(0, len(chunks), self._batch_size)
        ]
        
        logger.info(
            f"Embedding service starting batch processing: chunks={len(chunks)}, "
            f"batches={len(batches)}, batch_size={self._batch_size}, "
            f"provider='{self._provider.provider_name}', max_concurrency={self._max_concurrency}"
        )

        expected_dimension = self._provider.dimension
        warnings = []
        failures = 0

        # Define concurrent batch processor task
        async def process_batch(batch_chunks: list[Chunk]) -> list[list[float]]:
            nonlocal failures
            async with self._semaphore:
                texts = [chunk.content for chunk in batch_chunks]
                try:
                    result = await self._provider.generate_batch_embeddings(texts)
                    
                    if not result.success or not result.vectors:
                        raise EmbeddingError("Provider generate_batch_embeddings returned unsuccessful result.")
                        
                    # Validate vector dimensions
                    for vec in result.vectors:
                        actual_dim = len(vec)
                        if actual_dim != expected_dimension:
                            raise EmbeddingDimensionMismatch(
                                expected=expected_dimension,
                                actual=actual_dim
                            )
                    return result.vectors
                except Exception as e:
                    failures += 1
                    logger.error(f"Error processing embedding batch: {e}")
                    raise

        # 3. Process batches concurrently (subject to semaphore)
        try:
            tasks = [process_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks)
        except Exception as e:
            # Propagate the domain error
            logger.error(f"Embedding execution failed: {e}")
            raise

        # 4. Attach generated embeddings back to the original Chunk entities
        vector_index = 0
        all_vectors = [v for batch in batch_results for v in batch]
        
        for chunk, vec in zip(chunks, all_vectors):
            chunk.embedding = vec

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        settings = get_settings()

        statistics = {
            "total_chunks": len(chunks),
            "batch_size": self._batch_size,
            "batches_processed": len(batches),
            "provider": self._provider.provider_name,
            "model": settings.embedding_model,
            "dimension": expected_dimension,
            "failures": failures,
            "duration_ms": duration_ms,
        }

        # Structured Logging (no print statements)
        logger.info(
            f"Embedding generation completed: provider='{self._provider.provider_name}', "
            f"model='{settings.embedding_model}', batch_size={self._batch_size}, "
            f"dimension={expected_dimension}, duration={duration_ms:.1f}ms, "
            f"failures={failures}, warnings={len(warnings)}"
        )

        return ProcessingResult(
            success=True,
            duration_ms=duration_ms,
            warnings=warnings,
            statistics=statistics,
            payload=chunks,
        )
