"""
Backward compatibility layer.
Redirects to the new domain-level EmbeddingProvider ABC.
"""

from app.domain.services.embedding_provider import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
