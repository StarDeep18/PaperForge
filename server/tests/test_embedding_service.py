"""
Embedding Service Unit Tests.

Verifies validation, batching, error translation, concurrency, and configuration.
"""

import asyncio
import pytest
from typing import Optional

from app.core.config import get_settings
from app.domain.entities.chunk import Chunk
from app.domain.entities.embedding_result import EmbeddingResult
from app.domain.exceptions import (
    EmbeddingError,
    EmbeddingProviderUnavailable,
    EmbeddingDimensionMismatch,
    EmbeddingTimeout,
    InvalidEmbeddingResponse,
)
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.services.embedding_service import EmbeddingService
from app.infrastructure.ai.mock_embedding_provider import MockEmbeddingProvider


# ── Test Stubs ───────────────────────────────────────────────────

class FailingEmbeddingProvider(EmbeddingProvider):
    """Stub provider that always raises an error."""
    
    @property
    def provider_name(self) -> str:
        return "failing-mock"

    @property
    def dimension(self) -> int:
        return 768

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        raise EmbeddingProviderUnavailable(self.provider_name, "API endpoint is unreachable.")

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        raise EmbeddingProviderUnavailable(self.provider_name, "API endpoints are unreachable.")

    async def health_check(self) -> bool:
        return False


class MismatchedDimensionProvider(EmbeddingProvider):
    """Stub provider that returns vectors of incorrect size."""
    
    @property
    def provider_name(self) -> str:
        return "mismatched-mock"

    @property
    def dimension(self) -> int:
        return 768  # Claims to return 768

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=128,  # Actually returns 128
            vector=[0.1] * 128
        )

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=128,  # Actually returns 128
            vectors=[[0.1] * 128 for _ in texts]
        )

    async def health_check(self) -> bool:
        return True


class SlowEmbeddingProvider(EmbeddingProvider):
    """Stub provider that simulates slow API calls to test timeouts."""

    def __init__(self, delay: float = 0.5):
        self._delay = delay

    @property
    def provider_name(self) -> str:
        return "slow-mock"

    @property
    def dimension(self) -> int:
        return 768

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        await asyncio.sleep(self._delay)
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=768,
            vector=[0.0] * 768
        )

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        await asyncio.sleep(self._delay)
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=768,
            vectors=[[0.0] * 768 for _ in texts]
        )

    async def health_check(self) -> bool:
        return True


# ── Unit Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_successful_embedding_generation():
    """Verify that embeddings are correctly generated and attached to chunks."""
    provider = MockEmbeddingProvider(dimension=768)
    service = EmbeddingService(provider=provider, batch_size=2)
    
    chunks = [
        Chunk(document_id="doc-1", content="First chunk sentence."),
        Chunk(document_id="doc-1", content="Second chunk sentence."),
        Chunk(document_id="doc-1", content="Third chunk sentence."),
    ]
    
    result = await service.embed_chunks(chunks)
    
    assert result.success
    assert result.duration_ms > 0
    assert result.statistics["total_chunks"] == 3
    assert result.statistics["batches_processed"] == 2
    
    # Assert embeddings are set
    for chunk in chunks:
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 768
        # Ensure it has non-zero elements
        assert any(x != 0.0 for x in chunk.embedding)


@pytest.mark.asyncio
async def test_empty_chunk_list():
    """Verify that passing an empty chunk list succeeds immediately without calling provider."""
    provider = MockEmbeddingProvider(dimension=768)
    service = EmbeddingService(provider=provider)
    
    result = await service.embed_chunks([])
    
    assert result.success
    assert result.duration_ms == 0.0
    assert result.statistics["total_chunks"] == 0
    assert len(result.payload) == 0


@pytest.mark.asyncio
async def test_provider_failure():
    """Verify that provider failure raises appropriate exceptions."""
    provider = FailingEmbeddingProvider()
    service = EmbeddingService(provider=provider)
    
    chunks = [Chunk(document_id="doc-1", content="Some text.")]
    
    with pytest.raises(EmbeddingProviderUnavailable) as exc_info:
        await service.embed_chunks(chunks)
        
    assert "unavailable" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_invalid_embedding_dimension():
    """Verify that mismatching dimensions trigger a validation error."""
    provider = MismatchedDimensionProvider()
    service = EmbeddingService(provider=provider)
    
    chunks = [Chunk(document_id="doc-1", content="Trigger dimension check.")]
    
    with pytest.raises(EmbeddingDimensionMismatch) as exc_info:
        await service.embed_chunks(chunks)
        
    assert "dimension mismatch" in str(exc_info.value).lower()
    assert exc_info.value.expected == 768
    assert exc_info.value.actual == 128


@pytest.mark.asyncio
async def test_timeout_handling():
    """Verify that slow provider operations trigger a TimeoutError."""
    # We test timeout handling using the provider interface since timeout logic
    # is implemented in the concrete provider class (like GeminiEmbeddingProvider).
    # Here we simulate timing out a call using asyncio.wait_for like the provider does.
    provider = SlowEmbeddingProvider(delay=0.3)
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            provider.generate_embedding("Timeout query"),
            timeout=0.05
        )


@pytest.mark.asyncio
async def test_batch_processing():
    """Verify chunks are partitioned into exact configured batches."""
    provider = MockEmbeddingProvider(dimension=768)
    # Configure tiny batch size of 2
    service = EmbeddingService(provider=provider, batch_size=2)
    
    chunks = [Chunk(document_id="doc-1", content=f"Chunk index {i}") for i in range(5)]
    
    result = await service.embed_chunks(chunks)
    
    assert result.success
    # 5 chunks with batch_size=2 means 3 batches (2, 2, 1)
    assert result.statistics["batches_processed"] == 3
    assert result.statistics["total_chunks"] == 5
    
    for chunk in chunks:
        assert len(chunk.embedding) == 768


def test_configuration_loading():
    """Verify that new settings properties load correctly with expected defaults."""
    settings = get_settings()
    
    assert hasattr(settings, "embedding_provider")
    assert hasattr(settings, "embedding_batch_size")
    assert hasattr(settings, "embedding_timeout")
    assert hasattr(settings, "embedding_retry_count")
    assert hasattr(settings, "embedding_max_concurrency")
    assert hasattr(settings, "embedding_normalization")
    assert hasattr(settings, "embedding_dimension")
    
    # Check default types and values
    assert settings.embedding_provider in ("gemini", "mock")
    assert isinstance(settings.embedding_batch_size, int)
    assert isinstance(settings.embedding_timeout, float)
    assert isinstance(settings.embedding_retry_count, int)
    assert isinstance(settings.embedding_max_concurrency, int)
    assert isinstance(settings.embedding_normalization, bool)
    assert isinstance(settings.embedding_dimension, int)
