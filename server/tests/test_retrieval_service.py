"""
Retrieval Service Unit Tests.

Tests the complete retrieval pipeline: parameter validation, query embedding,
scoping, deduplication, parent chunk reconstruction, token budgets, and inspector.
"""

import math
import pytest
from typing import Optional

from app.core.config import get_settings
from app.domain.entities.chunk import Chunk
from app.domain.entities import MetadataFilter, RetrievalRequest, RetrievalResult, EmbeddingResult
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.services.embedding_service import EmbeddingService
from app.domain.services.vector_store_service import VectorStoreService
from app.domain.exceptions import (
    ContextBudgetExceeded,
    NoRelevantChunks,
    InvalidRetrievalRequest,
    QueryEmbeddingFailure,
)
from tests.test_vector_store_service import MockVectorStore


# ── Constant Embedding Provider Double ────────────────────────────

class ConstantEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider that returns a constant vector for testing.
    """

    def __init__(self, vector: list[float]):
        self._vector = vector

    @property
    def provider_name(self) -> str:
        return "constant-mock"

    @property
    def dimension(self) -> int:
        return len(self._vector)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=self.dimension,
            vector=self._vector,
        )

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=self.dimension,
            vectors=[self._vector] * len(texts),
        )

    async def health_check(self) -> bool:
        return True


# ── Test Suite ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normal_retrieval():
    """Verify that a normal retrieval query executes the entire pipeline."""
    query_vector = [1.0] + [0.0] * 767
    embed_provider = ConstantEmbeddingProvider(vector=query_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # Store dummy chunks matching query vector with distinct embeddings (non-duplicates)
    v1 = [1.0] + [0.0] * 767
    v2 = [0.7, 0.7] + [0.0] * 766
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="Chunk one text content is here.", embedding=v1),
        Chunk(id="c2", document_id="doc-1", content="Chunk two text content is here.", embedding=v2),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(
        embedding_provider=embed_provider,
        vector_store_service=vector_service,
    )
    
    req = RetrievalRequest(query="Grounding query", similarity_threshold=0.1)
    res = await retrieval_service.retrieve(req)
    
    assert res.query == "Grounding query"
    assert res.total_chunks == 2
    assert len(res.retrieved_chunks) == 2
    assert res.retrieval_duration > 0.0
    assert res.embedding_duration > 0.0
    assert res.search_duration > 0.0
    
    # Check context window
    assert res.context_window is not None
    assert len(res.context_window.ordered_chunks) == 2
    assert res.context_window.estimated_tokens > 0
    
    # Check inspector
    assert res.inspector is not None
    assert res.inspector.query == "Grounding query"
    assert len(res.inspector.retrieved_chunk_ids) == 2
    assert len(res.inspector.similarity_scores) == 2
    assert res.inspector.ranking == [1, 2]


@pytest.mark.asyncio
async def test_empty_query():
    """Verify that an empty query raises InvalidRetrievalRequest."""
    embed_provider = ConstantEmbeddingProvider(vector=[0.1] * 768)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    with pytest.raises(InvalidRetrievalRequest) as exc_info:
        await retrieval_service.retrieve(RetrievalRequest(query="  "))
    assert "query" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_invalid_threshold():
    """Verify that an invalid threshold raises InvalidRetrievalRequest."""
    embed_provider = ConstantEmbeddingProvider(vector=[0.1] * 768)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    with pytest.raises(InvalidRetrievalRequest) as exc_info:
        await retrieval_service.retrieve(
            RetrievalRequest(query="query", similarity_threshold=1.5)
        )
    assert "threshold" in str(exc_info.value).lower()
    
    with pytest.raises(InvalidRetrievalRequest) as exc_info:
        await retrieval_service.retrieve(
            RetrievalRequest(query="query", similarity_threshold=-0.1)
        )
    assert "threshold" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_metadata_filters():
    """Verify that document_ids and workspace_ids filters are applied properly."""
    constant_vector = [0.1] * 768
    embed_provider = ConstantEmbeddingProvider(vector=constant_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    chunks = [
        Chunk(id="c1", document_id="doc-A", content="Text from doc A", embedding=constant_vector),
        Chunk(id="c2", document_id="doc-B", content="Text from doc B", embedding=constant_vector),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    req = RetrievalRequest(
        query="grounding",
        document_ids=["doc-B"],
        similarity_threshold=0.1,
    )
    res = await retrieval_service.retrieve(req)
    assert res.total_chunks == 1
    assert res.retrieved_chunks[0].document_id == "doc-B"


@pytest.mark.asyncio
async def test_duplicate_removal():
    """Verify that identical chunk IDs and highly similar semantic duplicate chunks are removed."""
    constant_vector = [0.1] * 768
    embed_provider = ConstantEmbeddingProvider(vector=constant_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # c1 and c2 have identical embedding vectors (cosine similarity = 1.0)
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="Chunk A text", embedding=constant_vector),
        Chunk(id="c2", document_id="doc-1", content="Highly similar text copy", embedding=constant_vector),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    req = RetrievalRequest(query="grounding", similarity_threshold=0.1)
    res = await retrieval_service.retrieve(req)
    
    # The duplicate (c2) should be removed because its vector is identical to c1
    assert res.total_chunks == 1
    assert res.retrieved_chunks[0].id == "c1"


@pytest.mark.asyncio
async def test_parent_reconstruction():
    """Verify that multiple child chunks referencing the same parent are merged when merge policy is enabled."""
    query_vector = [1.0] + [0.0] * 767
    embed_provider = ConstantEmbeddingProvider(vector=query_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # Two child chunks pointing to parent-123 with distinct embeddings (non-duplicates)
    v1 = [1.0] + [0.0] * 767
    v2 = [0.7, 0.7] + [0.0] * 766
    chunks = [
        Chunk(
            id="c1",
            document_id="doc-1",
            content="Child fragment one",
            parent_chunk_id="parent-123",
            parent_content="This is the full parent continuous text that incorporates child one and child two.",
            embedding=v1,
        ),
        Chunk(
            id="c2",
            document_id="doc-1",
            content="Child fragment two",
            parent_chunk_id="parent-123",
            parent_content="This is the full parent continuous text that incorporates child one and child two.",
            embedding=v2,
        ),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    req = RetrievalRequest(query="grounding", similarity_threshold=0.1)
    res = await retrieval_service.retrieve(req)
    
    # They should be merged into a single parent representation
    assert res.total_chunks == 1
    merged = res.retrieved_chunks[0]
    assert merged.id == "parent-parent-123"
    assert merged.content == "This is the full parent continuous text that incorporates child one and child two."


@pytest.mark.asyncio
async def test_context_budgeting():
    """Verify that chunks exceeding the token budget are discarded."""
    query_vector = [1.0] + [0.0] * 767
    embed_provider = ConstantEmbeddingProvider(vector=query_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # Add two chunks of length 80 characters each (~20 tokens each) with distinct embeddings (non-duplicates)
    v1 = [1.0] + [0.0] * 767
    v2 = [0.7, 0.7] + [0.0] * 766
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="A" * 80, embedding=v1),
        Chunk(id="c2", document_id="doc-1", content="B" * 80, embedding=v2),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    # Force max_context_tokens to 30 (so only one chunk fits, since each is ~20 tokens)
    req = RetrievalRequest(query="grounding", similarity_threshold=0.1, max_context_tokens=30)
    res = await retrieval_service.retrieve(req)
    
    assert res.total_chunks == 1
    assert len(res.retrieved_chunks) == 1
    assert res.context_window.estimated_tokens <= 30
    assert res.context_window.remaining_budget >= 10


@pytest.mark.asyncio
async def test_sorting():
    """Verify retrieved chunks are ordered descending by similarity score."""
    # We want query to match v1 closer than v2
    query_vector = [1.0] + [0.0] * 767
    embed_provider = ConstantEmbeddingProvider(vector=query_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # v1 is identical to query (score = 1.0)
    # v2 is orthogonal (score = 0.707)
    v1 = [1.0] + [0.0] * 767
    v2 = [0.7, 0.7] + [0.0] * 766
    
    # Add chunks in reversed relevance order (c2 first, c1 second)
    chunks = [
        Chunk(id="c2", document_id="doc-1", content="Orthogonal chunk", embedding=v2),
        Chunk(id="c1", document_id="doc-1", content="Exact match chunk", embedding=v1),
    ]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    req = RetrievalRequest(query="grounding", similarity_threshold=0.01)
    res = await retrieval_service.retrieve(req)
    
    assert res.total_chunks == 2
    # c1 must rank first
    assert res.retrieved_chunks[0].id == "c1"
    assert res.retrieved_chunks[1].id == "c2"


@pytest.mark.asyncio
async def test_no_relevant_chunks_exception():
    """Verify raising NoRelevantChunks when similarity filtering yields empty results."""
    # query is [1.0, 0.0, ...]
    query_vector = [1.0] + [0.0] * 767
    embed_provider = ConstantEmbeddingProvider(vector=query_vector)
    db = MockVectorStore(dimension=768)
    vector_service = VectorStoreService(vector_store=db)
    
    # Store chunk with low similarity score (v1 is orthogonal, score = 0.0)
    v1 = [0.0] + [1.0] + [0.0] * 766
    chunks = [Chunk(id="c1", document_id="doc-1", content="Orthogonal chunk", embedding=v1)]
    await vector_service.add_chunks(chunks)
    
    from app.domain.services.retrieval_service import RetrievalService
    retrieval_service = RetrievalService(embed_provider, vector_service)
    
    # Request high threshold of 0.9 (should yield empty matching)
    req = RetrievalRequest(query="grounding", similarity_threshold=0.9)
    
    with pytest.raises(NoRelevantChunks) as exc_info:
        await retrieval_service.retrieve(req)
    assert "no chunks found" in str(exc_info.value).lower()
