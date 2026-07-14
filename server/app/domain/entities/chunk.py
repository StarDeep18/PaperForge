"""
Chunk Entity.

Represents a text fragment from a document, used for vector search
and RAG retrieval. Follows a parent-child chunking strategy.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.core.security import utc_now


@dataclass
class Chunk:
    """
    A text chunk extracted from a document for embedding and retrieval.

    Child chunks (smaller, ~512 tokens) are stored in the vector database
    for high-precision semantic search. Each child references a parent chunk
    (larger, ~1500 tokens) stored in SQLite, which provides richer context
    to the LLM during generation.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str = ""
    parent_content: Optional[str] = None  # Larger context window
    parent_chunk_id: Optional[str] = None  # Added
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 0  # Added
    character_start: int = 0  # Added
    character_end: int = 0  # Added
    page_relative_start: Optional[int] = None  # Added for page-specific navigation
    page_relative_end: Optional[int] = None  # Added for page-specific navigation
    token_count: int = 0
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def retrieval_metadata(self) -> dict:
        """Metadata dict for vector store storage."""
        meta = {
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "character_start": self.character_start,
            "character_end": self.character_end,
            "created_at": self.created_at.isoformat(),
        }
        if self.page_relative_start is not None:
            meta["page_relative_start"] = self.page_relative_start
        if self.page_relative_end is not None:
            meta["page_relative_end"] = self.page_relative_end
        if self.parent_chunk_id:
            meta["parent_chunk_id"] = self.parent_chunk_id
        if self.page_number is not None:
            meta["page_number"] = self.page_number
        if self.section_header:
            meta["section_header"] = self.section_header
            meta["section_heading"] = self.section_header  # support both naming conventions
        meta.update(self.metadata)
        return meta


@dataclass
class SearchResult:
    """
    A single result from a vector similarity search.

    Contains the matched chunk, its similarity score, and
    the parent context for richer LLM generation.
    """

    chunk_id: str = ""
    document_id: str = ""
    content: str = ""
    parent_content: Optional[str] = None
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    score: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def context_text(self) -> str:
        """Return parent content if available, otherwise chunk content."""
        return self.parent_content or self.content


@dataclass
class ProcessingResult:
    """
    Standardized result wrapper for application and domain service operations.

    Provides uniform structures for success flags, duration tracking, warnings,
    statistics, and output payloads across different services.
    """

    success: bool
    duration_ms: float
    warnings: list[str]
    statistics: dict
    payload: list[Chunk]
