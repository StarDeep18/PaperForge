"""
Vector Store Service Unit Tests.

Verifies validations, batch writes/deletes, similarity search logic,
metadata filters, exception scenarios, and settings defaults.
"""

import math
import pytest
from typing import Optional

from app.core.config import get_settings
from app.domain.entities.chunk import Chunk
from app.domain.entities.metadata_filter import MetadataFilter
from app.domain.entities.vector_store_result import VectorSearchResult, VectorStoreResult
from app.domain.repositories.vector_store import VectorStore
from app.domain.services.vector_store_service import VectorStoreService
from app.domain.exceptions import (
    DuplicateChunk,
    VectorInsertError,
    VectorSearchError,
    VectorDeleteError,
)


# ── Cosine Similarity Helper ────────────────────────────────────

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(v1, v2))
    n1 = math.sqrt(sum(x * x for x in v1))
    n2 = math.sqrt(sum(x * x for x in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


# ── In-Memory Vector Store Double ────────────────────────────────

class MockVectorStore(VectorStore):
    """
    In-memory VectorStore double to test search, pagination, filtering,
    and thresholding locally without database servers or build dependencies.
    """

    def __init__(self, dimension: int = 768):
        self._chunks: dict[str, Chunk] = {}
        self._dimension = dimension

    async def add_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        for c in chunks:
            self._chunks[c.id] = c
        return VectorStoreResult(
            success=True,
            operation="insert",
            processed_count=len(chunks),
            duration=1.0,
        )

    async def update_chunks(self, chunks: list[Chunk]) -> VectorStoreResult:
        for c in chunks:
            self._chunks[c.id] = c
        return VectorStoreResult(
            success=True,
            operation="update",
            processed_count=len(chunks),
            duration=1.0,
        )

    async def delete_chunks(self, chunk_ids: list[str]) -> VectorStoreResult:
        deleted = 0
        for cid in chunk_ids:
            if cid in self._chunks:
                del self._chunks[cid]
                deleted += 1
        return VectorStoreResult(
            success=True,
            operation="delete_chunks",
            processed_count=deleted,
            duration=1.0,
        )

    async def delete_document(self, document_id: str) -> VectorStoreResult:
        to_delete = [cid for cid, c in self._chunks.items() if c.document_id == document_id]
        for cid in to_delete:
            del self._chunks[cid]
        return VectorStoreResult(
            success=True,
            operation="delete_document",
            processed_count=len(to_delete),
            duration=1.0,
        )

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        metadata_filter: Optional[MetadataFilter] = None,
        score_threshold: float = 0.3,
    ) -> list[VectorSearchResult]:
        results = []
        for cid, c in self._chunks.items():
            # Scoping filters via MetadataFilter
            if metadata_filter:
                if metadata_filter.document_ids and c.document_id not in metadata_filter.document_ids:
                    continue
                if metadata_filter.collection_id and c.metadata.get("collection_id") != metadata_filter.collection_id:
                    continue
                if metadata_filter.workspace_id and c.metadata.get("workspace_id") != metadata_filter.workspace_id:
                    continue
                if metadata_filter.author and c.metadata.get("author") != metadata_filter.author:
                    continue
                if metadata_filter.year and c.metadata.get("year") != metadata_filter.year:
                    continue
                if metadata_filter.paper_type and c.metadata.get("paper_type") != metadata_filter.paper_type:
                    continue

            # Calculate cosine score
            score = cosine_similarity(query_embedding, c.embedding)
            if score < score_threshold:
                continue

            results.append(
                VectorSearchResult(
                    chunk=c,
                    distance=1.0 - score,
                    raw_score=score,
                    normalized_score=score,
                    document_id=c.document_id,
                    chunk_id=cid,
                    metadata=c.metadata,
                    provider="mock-db",
                )
            )
        
        # Sort by score descending and limit results
        results.sort(key=lambda r: r.normalized_score, reverse=True)
        return results[:top_k]

    async def health_check(self) -> dict:
        doc_ids = {c.document_id for c in self._chunks.values()}
        return {
            "provider": "mock-db",
            "status": "healthy",
            "collection_count": 1,
            "document_count": len(doc_ids),
            "embedding_dimension": self._dimension,
            "database_version": "1.0.0-mock",
        }

    async def count(self, document_id: Optional[str] = None) -> int:
        if document_id:
            return sum(1 for c in self._chunks.values() if c.document_id == document_id)
        return len(self._chunks)


# ── Unit Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_insertion():
    """Verify that chunks are partitioned and stored successfully."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="Text one.", embedding=[0.1] * 768),
        Chunk(id="c2", document_id="doc-1", content="Text two.", embedding=[0.2] * 768),
        Chunk(id="c3", document_id="doc-2", content="Text three.", embedding=[0.3] * 768),
    ]
    
    result = await service.add_chunks(chunks)
    assert result.success
    assert result.operation == "insert"
    assert result.processed_count == 3
    assert await db.count() == 3


@pytest.mark.asyncio
async def test_duplicate_chunk_ids():
    """Verify duplicate IDs in the insertion payload raises DuplicateChunk."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    chunks = [
        Chunk(id="dup", document_id="doc-1", content="Content one.", embedding=[0.1] * 768),
        Chunk(id="dup", document_id="doc-1", content="Content two.", embedding=[0.2] * 768),
    ]
    
    with pytest.raises(DuplicateChunk):
        await service.add_chunks(chunks)


@pytest.mark.asyncio
async def test_invalid_vectors_empty():
    """Verify empty/null vector fails validation."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    chunks = [Chunk(id="c1", document_id="doc-1", content="Text.", embedding=None)]
    
    with pytest.raises(VectorInsertError) as exc_info:
        await service.add_chunks(chunks)
    assert "empty" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_invalid_vectors_wrong_dimension():
    """Verify incorrect embedding dimension raises error."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    # 512 dimensions instead of 768
    chunks = [Chunk(id="c1", document_id="doc-1", content="Text.", embedding=[0.1] * 512)]
    
    with pytest.raises(VectorInsertError) as exc_info:
        await service.add_chunks(chunks)
    assert "dimension" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_invalid_vectors_nan():
    """Verify NaN embedding raises validation error."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    vec_nan = [0.1] * 767 + [float("nan")]
    chunks = [Chunk(id="c1", document_id="doc-1", content="Text.", embedding=vec_nan)]
    
    with pytest.raises(VectorInsertError) as exc_info:
        await service.add_chunks(chunks)
    assert "nan" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_similarity_search():
    """Verify search yields correct cosine similarity ranking."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    # Insert chunks with distinctive direction vectors
    # c1 is identical to query vector [1.0, 0.0, ...]
    v1 = [1.0] + [0.0] * 767
    v2 = [0.5] + [0.5] * 767  # orthogonal elements
    
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="Close text.", embedding=v1),
        Chunk(id="c2", document_id="doc-1", content="Medium text.", embedding=v2),
    ]
    await service.add_chunks(chunks)
    
    # Search query matches v1 perfectly
    query = [1.0] + [0.0] * 767
    results = await service.similarity_search(query_embedding=query, top_k=2, score_threshold=0.01)
    
    assert len(results) == 2
    assert results[0].chunk_id == "c1"
    assert math.isclose(results[0].normalized_score, 1.0, rel_tol=1e-5)
    assert results[0].raw_score == results[0].normalized_score
    assert results[0].distance == 0.0
    assert results[1].chunk_id == "c2"
    assert results[1].normalized_score < 0.8


@pytest.mark.asyncio
async def test_invalid_similarity_threshold():
    """Verify threshold validations in search."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    query = [0.1] * 768
    
    # Threshold > 1.0
    with pytest.raises(VectorSearchError) as exc_info:
        await service.similarity_search(query_embedding=query, score_threshold=1.5)
    assert "threshold" in str(exc_info.value).lower()

    # Threshold < 0.0
    with pytest.raises(VectorSearchError) as exc_info:
        await service.similarity_search(query_embedding=query, score_threshold=-0.1)
    assert "threshold" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_metadata_filtering():
    """Verify scoping queries by document_id and collection_id using MetadataFilter."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    vec = [0.1] * 768
    chunks = [
        Chunk(id="c1", document_id="doc-A", content="A", embedding=vec, metadata={"collection_id": "coll-1"}),
        Chunk(id="c2", document_id="doc-B", content="B", embedding=vec, metadata={"collection_id": "coll-1"}),
        Chunk(id="c3", document_id="doc-C", content="C", embedding=vec, metadata={"collection_id": "coll-2"}),
    ]
    await service.add_chunks(chunks)
    
    # Filter by single document id
    res_doc = await service.similarity_search(
        query_embedding=vec,
        metadata_filter=MetadataFilter(document_ids=["doc-B"]),
    )
    assert len(res_doc) == 1
    assert res_doc[0].document_id == "doc-B"
    
    # Filter by collection id
    res_coll = await service.similarity_search(
        query_embedding=vec,
        metadata_filter=MetadataFilter(collection_id="coll-1"),
    )
    assert len(res_coll) == 2
    assert {r.chunk_id for r in res_coll} == {"c1", "c2"}


@pytest.mark.asyncio
async def test_delete_document():
    """Verify document deletion removes all associated chunks."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    vec = [0.1] * 768
    chunks = [
        Chunk(id="c1", document_id="doc-delete", content="A", embedding=vec),
        Chunk(id="c2", document_id="doc-delete", content="B", embedding=vec),
        Chunk(id="c3", document_id="doc-keep", content="C", embedding=vec),
    ]
    await service.add_chunks(chunks)
    
    res = await service.delete_document("doc-delete")
    assert res.success
    assert res.processed_count == 2
    
    assert await db.count() == 1
    assert (await db.count("doc-delete")) == 0


@pytest.mark.asyncio
async def test_delete_chunks():
    """Verify chunk IDs batch deletion."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    vec = [0.1] * 768
    chunks = [
        Chunk(id="c1", document_id="doc-1", content="A", embedding=vec),
        Chunk(id="c2", document_id="doc-1", content="B", embedding=vec),
    ]
    await service.add_chunks(chunks)
    
    res = await service.delete_chunks(["c1"])
    assert res.success
    assert res.processed_count == 1
    assert await db.count() == 1


@pytest.mark.asyncio
async def test_health_check():
    """Verify diagnostics dictionary payload."""
    db = MockVectorStore(dimension=768)
    service = VectorStoreService(vector_store=db)
    
    health = await service.health_check()
    assert health["provider"] == "mock-db"
    assert health["status"] == "healthy"
    assert health["embedding_dimension"] == 768
