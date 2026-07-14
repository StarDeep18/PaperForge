"""
Retrieval Service.

Orchestrates the entire document retrieval pipeline: validates request parameters,
generates query embeddings, fetches matching chunks from the vector database,
applies semantic deduplication, consolidates parent context blocks, ranks items,
enforces context budgets, and returns unified diagnostics.
"""

import math
import time
from typing import Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.metadata_filter import MetadataFilter
from app.domain.entities.retrieval import (
    RetrievalRequest,
    RetrievalResult,
    ContextWindow,
    RetrievalInspector,
)
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.services.vector_store_service import VectorStoreService
from app.domain.exceptions import (
    RetrievalError,
    ContextBudgetExceeded,
    NoRelevantChunks,
    InvalidRetrievalRequest,
    QueryEmbeddingFailure,
)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(v1, v2))
    n1 = math.sqrt(sum(x * x for x in v1))
    n2 = math.sqrt(sum(x * x for x in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


class RetrievalService:
    """
    Business orchestration service managing document retrieval pipeline for LLM grounding.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store_service: VectorStoreService,
    ):
        self._embedding_provider = embedding_provider
        self._vector_store_service = vector_store_service

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """
        Execute the retrieval pipeline and assemble the grounded context window.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        warnings = []

        # ── 1. Validation ──────────────────────────────────────────────
        if not request.query or not request.query.strip():
            raise InvalidRetrievalRequest("query", "Query text cannot be empty or whitespaces.")

        top_k = request.top_k or settings.retrieval_default_top_k
        if top_k <= 0:
            raise InvalidRetrievalRequest("top_k", "Must be greater than 0.")

        threshold = (
            request.similarity_threshold
            if request.similarity_threshold is not None
            else settings.retrieval_minimum_similarity
        )
        if threshold < 0.0 or threshold > 1.0:
            raise InvalidRetrievalRequest("similarity_threshold", "Must be between 0.0 and 1.0.")

        max_tokens = (
            request.max_context_tokens
            if request.max_context_tokens is not None
            else settings.retrieval_max_context_tokens
        )
        if max_tokens <= 0:
            raise InvalidRetrievalRequest("max_context_tokens", "Must be greater than 0.")

        # ── 2. Generate Query Embedding ──────────────────────────────
        embed_start = time.perf_counter()
        try:
            embed_res = await self._embedding_provider.generate_embedding(request.query)
            if not embed_res.success or not embed_res.vector:
                raise QueryEmbeddingFailure(request.query, "Embedding provider returned unsuccessful payload.")
            query_vector = embed_res.vector
        except Exception as e:
            logger.error(f"Retrieval query embedding generation failed: {e}")
            raise QueryEmbeddingFailure(request.query, str(e)) from e
        embedding_duration = (time.perf_counter() - embed_start) * 1000.0

        # ── 3. Vector Search & Metadata Filtering ─────────────────────
        search_start = time.perf_counter()
        # Compile metadata filter object (prefer workspace/document list parameter shortcuts if specified)
        m_filter = request.metadata_filter or MetadataFilter()
        if request.document_ids:
            m_filter.document_ids = request.document_ids
        if request.workspace_id:
            m_filter.workspace_id = request.workspace_id

        try:
            # Query vector database
            search_results = await self._vector_store_service.similarity_search(
                query_embedding=query_vector,
                top_k=top_k,
                metadata_filter=m_filter,
                score_threshold=threshold,
            )
        except Exception as e:
            logger.error(f"Retrieval vector database search failed: {e}")
            raise RetrievalError(f"Vector search failed: {e}") from e
        search_duration = (time.perf_counter() - search_start) * 1000.0

        # Map filters dictionary representation for logging and inspector
        applied_filters = {
            "document_ids": m_filter.document_ids,
            "collection_id": m_filter.collection_id,
            "workspace_id": m_filter.workspace_id,
            "tags": m_filter.tags,
            "author": m_filter.author,
            "year": m_filter.year,
            "paper_type": m_filter.paper_type,
        }
        # Trim out null filters
        applied_filters = {k: v for k, v in applied_filters.items() if v is not None}

        # ── 4. Similarity Threshold ──────────────────────────────────
        # similarity threshold was already checked inside similarity_search, but we can verify here
        filtered_results = [r for r in search_results if r.normalized_score >= threshold]

        # ── 5. Duplicate Removal ──────────────────────────────────────
        # Deduplicate identical chunk IDs
        unique_results = []
        seen_ids = set()
        for r in filtered_results:
            if r.chunk_id not in seen_ids:
                seen_ids.add(r.chunk_id)
                unique_results.append(r)

        # Deduplicate highly similar vector chunks
        final_dedup_results = []
        dup_threshold = settings.retrieval_duplicate_threshold
        
        chunks_discarded = 0
        for r in unique_results:
            is_dup = False
            # If embedding is present (common during unit test doubles & query returns)
            if r.chunk.embedding:
                for kept_r in final_dedup_results:
                    if kept_r.chunk.embedding:
                        sim = cosine_similarity(r.chunk.embedding, kept_r.chunk.embedding)
                        if sim > dup_threshold:
                            is_dup = True
                            chunks_discarded += 1
                            break
            if not is_dup:
                final_dedup_results.append(r)

        # ── 6. Parent Chunk Merge ──────────────────────────────────────
        merge_policy = settings.retrieval_chunk_merge_policy
        merged_chunks = []
        
        if merge_policy == "merge_parent" and final_dedup_results:
            # Group child chunks by parent_chunk_id
            parent_groups = {}
            unmergeable = []
            
            for r in final_dedup_results:
                pid = r.chunk.parent_chunk_id
                doc_id = r.chunk.document_id
                # Only merge if it belongs to a parent group (has parent_chunk_id)
                if pid:
                    parent_groups.setdefault((doc_id, pid), []).append(r)
                else:
                    unmergeable.append(r)
            
            # Process merges
            for (doc_id, pid), group in parent_groups.items():
                if len(group) > 1:
                    # Consolidate multiple children pointing to the same parent
                    first = group[0]
                    # Create parent chunk representant
                    merged_content = first.chunk.parent_content or "\n\n".join(
                        c.chunk.content for c in sorted(group, key=lambda x: x.chunk.chunk_index)
                    )
                    
                    # Estimate combined token/offset details
                    merged_chunk = Chunk(
                        id=f"parent-{pid}",
                        document_id=doc_id,
                        content=merged_content,
                        parent_chunk_id=pid,
                        parent_content=first.chunk.parent_content,
                        page_number=first.chunk.page_number,
                        section_header=first.chunk.section_header,
                        # Select best score for parent representation
                        metadata={
                            "merged_child_ids": [x.chunk_id for x in group],
                            "parent_merged": True,
                        },
                    )
                    
                    # Use best score from group
                    best_score = max(x.normalized_score for x in group)
                    best_distance = min(x.distance for x in group) if group[0].distance is not None else None
                    
                    # Keep track of custom metadata
                    merged_chunks.append(
                        (merged_chunk, best_score, best_distance, first.provider)
                    )
                else:
                    # Single child, keep as is
                    single = group[0]
                    merged_chunks.append((single.chunk, single.normalized_score, single.distance, single.provider))
                    
            for item in unmergeable:
                merged_chunks.append((item.chunk, item.normalized_score, item.distance, item.provider))
        else:
            # No merging, keep child chunks raw
            for r in final_dedup_results:
                merged_chunks.append((r.chunk, r.normalized_score, r.distance, r.provider))

        # ── 7. Sort by Relevance ──────────────────────────────────────
        # Sort merged chunks descending by score
        merged_chunks.sort(key=lambda x: x[1], reverse=True)

        # ── 8. Token Budget & Context Window Assembly ─────────────────
        final_chunks = []
        estimated_tokens = 0
        
        for chunk, score, distance, provider in merged_chunks:
            # Estimate token size conservatively
            chunk_tokens = len(chunk.content) // 4
            
            # If adding this chunk fits under budget
            if estimated_tokens + chunk_tokens <= max_tokens:
                final_chunks.append(chunk)
                estimated_tokens += chunk_tokens
            else:
                # Discard chunk due to budget overflow
                chunks_discarded += 1

        remaining_budget = max(0, max_tokens - estimated_tokens)
        context_window = ContextWindow(
            ordered_chunks=final_chunks,
            estimated_tokens=estimated_tokens,
            remaining_budget=remaining_budget,
        )

        # Raise NoRelevantChunks exception if empty context window
        if not final_chunks:
            raise NoRelevantChunks(request.query, threshold)

        # ── 9. Diagnostics & RetrievalInspector ──────────────────────
        retrieval_duration = (time.perf_counter() - start_time) * 1000.0
        
        inspector = RetrievalInspector(
            query=request.query,
            retrieved_chunk_ids=[c.id for c in final_chunks],
            similarity_scores=[
                next(item[1] for item in merged_chunks if item[0].id == c.id) for c in final_chunks
            ],
            ranking=list(range(1, len(final_chunks) + 1)),
            metadata=[c.retrieval_metadata for c in final_chunks],
            processing_time=retrieval_duration,
            applied_filters=applied_filters,
        )

        # ── 10. Logging Telemetry ────────────────────────────────────
        logger.info(
            f"Retrieval completed: query_len={len(request.query)}, "
            f"retrieval_duration={retrieval_duration:.1f}ms, embedding_duration={embedding_duration:.1f}ms, "
            f"search_duration={search_duration:.1f}ms, chunks_retrieved={len(final_chunks)}, "
            f"chunks_discarded={chunks_discarded}, token_estimate={estimated_tokens}, "
            f"filters_applied={list(applied_filters.keys())}"
        )

        return RetrievalResult(
            query=request.query,
            retrieved_chunks=final_chunks,
            total_chunks=len(final_chunks),
            retrieval_duration=retrieval_duration,
            embedding_duration=embedding_duration,
            search_duration=search_duration,
            applied_filters=applied_filters,
            warnings=warnings,
            context_window=context_window,
            inspector=inspector,
        )
