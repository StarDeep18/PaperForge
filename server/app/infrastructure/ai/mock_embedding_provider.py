"""
Mock Embedding Provider.

Used for offline development and testing. Generates deterministic vectors.
"""

import time
import hashlib
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.entities.embedding_result import EmbeddingResult


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock implementation of EmbeddingProvider.
    
    Generates deterministic pseudo-random vectors based on the text hash
    to allow consistent local offline testing.
    """

    def __init__(self, dimension: int = 768):
        self._dimension = dimension
        self._provider_name = "mock"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic float list of size `dimension` from a string."""
        # Use hashlib to create a repeatable sequence of floats
        hasher = hashlib.sha256(text.encode("utf-8"))
        seed = hasher.digest()
        
        # Expand seed to the required dimension
        vector = []
        for i in range(self._dimension):
            # Deterministic calculation using seed bytes and index
            val = (seed[i % len(seed)] + i) % 256
            # Normalize to [-1.0, 1.0] range
            vector.append((val / 127.5) - 1.0)
            
        return vector

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        start_time = time.perf_counter()
        
        # Generate dummy vector
        vector = self._generate_vector(text)
        
        duration = time.perf_counter() - start_time
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=self.dimension,
            vector=vector,
            duration=duration,
            warnings=[],
        )

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        start_time = time.perf_counter()
        
        vectors = [self._generate_vector(text) for text in texts]
        
        duration = time.perf_counter() - start_time
        return EmbeddingResult(
            success=True,
            provider=self.provider_name,
            dimension=self.dimension,
            vectors=vectors,
            duration=duration,
            warnings=[],
        )

    async def health_check(self) -> bool:
        return True
