"""
Retrieval Domain Models.

Standardized models for LLM context assembly, diagnostics, and debugging.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.domain.entities.chunk import Chunk
from app.domain.entities.metadata_filter import MetadataFilter


@dataclass
class RetrievalRequest:
    """
    Structured retrieval request parameters.
    """

    query: str
    workspace_id: Optional[str] = None
    document_ids: Optional[list[str]] = None
    metadata_filter: Optional[MetadataFilter] = None
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    max_context_tokens: Optional[int] = None


@dataclass
class ContextWindow:
    """
    Assembled context window details ready for the LLM.
    """

    ordered_chunks: list[Chunk] = field(default_factory=list)
    estimated_tokens: int = 0
    remaining_budget: int = 0


@dataclass
class RetrievalInspector:
    """
    Diagnostics details exposing metadata, scores, rankings, and processing times.
    """

    query: str
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    similarity_scores: list[float] = field(default_factory=list)
    ranking: list[int] = field(default_factory=list)
    metadata: list[dict] = field(default_factory=list)
    processing_time: float = 0.0  # milliseconds
    applied_filters: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """
    Unified payload returned to the application/generation layer.
    """

    query: str
    retrieved_chunks: list[Chunk]
    total_chunks: int
    retrieval_duration: float = 0.0  # milliseconds
    embedding_duration: float = 0.0  # milliseconds
    search_duration: float = 0.0  # milliseconds
    applied_filters: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    context_window: Optional[ContextWindow] = None
    inspector: Optional[RetrievalInspector] = None
