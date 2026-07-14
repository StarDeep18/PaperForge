"""
Embedding Result Model.

Represents the output of an embedding generation request.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmbeddingResult:
    """
    Standardized payload wrapping the results of an embedding operation.
    
    Ensures that raw lists of vectors are not returned directly.
    Supports both single-vector and batch-vector generation.
    """

    success: bool
    provider: str
    dimension: int
    vector: Optional[list[float]] = None
    vectors: Optional[list[list[float]]] = None
    duration: float = 0.0  # seconds
    warnings: list[str] = field(default_factory=list)
