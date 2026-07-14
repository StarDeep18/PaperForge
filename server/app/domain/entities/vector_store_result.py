"""
Vector Store Result Models.

Standardized models for similarity search outputs and write operation stats.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.domain.entities.chunk import Chunk


@dataclass
class VectorSearchResult:
    """
    Standardized payload representing a single chunk matched during similarity search.
    """

    chunk: Chunk
    distance: Optional[float] = None
    raw_score: Optional[float] = None
    normalized_score: Optional[float] = None
    document_id: str = ""
    chunk_id: str = ""
    metadata: dict = field(default_factory=dict)
    provider: str = "chroma"
    retrieval_time: float = 0.0  # seconds


@dataclass
class VectorStoreResult:
    """
    Standardized summary reporting execution stats of a write, delete, or management operation.
    """

    success: bool
    operation: str  # e.g., "insert", "delete", "update", "create_collection"
    processed_count: int
    duration: float = 0.0  # milliseconds
    warnings: list[str] = field(default_factory=list)
