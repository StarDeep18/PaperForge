"""
Document (Paper) Entity.

Represents a research paper uploaded to PaperForge.
This is a pure domain object with no framework dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.core.security import utc_now


class DocumentStatus(str, Enum):
    """Processing lifecycle of a document."""

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document file types."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


@dataclass
class DocumentMetadata:
    """Extracted metadata from a research paper."""

    title: Optional[str] = None
    authors: Optional[list[str]] = None
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: Optional[list[str]] = None
    page_count: int = 0
    word_count: int = 0


@dataclass
class Document:
    """
    Core domain entity representing a research paper.

    A Document goes through a processing pipeline:
    UPLOADED → PARSING → PARSED → CHUNKING → EMBEDDING → READY

    Each state transition is meaningful and tracked.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    filename: str = ""
    original_filename: str = ""
    file_path: str = ""
    file_size: int = 0
    file_type: DocumentType = DocumentType.PDF
    status: DocumentStatus = DocumentStatus.UPLOADED
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    collection_id: Optional[str] = None
    raw_text: Optional[str] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def mark_parsing(self) -> None:
        """Transition to PARSING status."""
        self.status = DocumentStatus.PARSING
        self.updated_at = utc_now()

    def mark_parsed(self, raw_text: str, metadata: DocumentMetadata) -> None:
        """Transition to PARSED after successful text extraction."""
        self.status = DocumentStatus.PARSED
        self.raw_text = raw_text
        self.metadata = metadata
        self.updated_at = utc_now()

    def mark_chunking(self) -> None:
        """Transition to CHUNKING status."""
        self.status = DocumentStatus.CHUNKING
        self.updated_at = utc_now()

    def mark_embedding(self) -> None:
        """Transition to EMBEDDING status."""
        self.status = DocumentStatus.EMBEDDING
        self.updated_at = utc_now()

    def mark_ready(self, chunk_count: int) -> None:
        """Transition to READY — document is fully processed."""
        self.status = DocumentStatus.READY
        self.chunk_count = chunk_count
        self.updated_at = utc_now()

    def mark_failed(self, error: str) -> None:
        """Transition to FAILED with an error message."""
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.updated_at = utc_now()

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY

    @property
    def is_processing(self) -> bool:
        return self.status in (
            DocumentStatus.PARSING,
            DocumentStatus.CHUNKING,
            DocumentStatus.EMBEDDING,
        )

    @property
    def display_title(self) -> str:
        """Return the paper title or fall back to filename."""
        if self.metadata and self.metadata.title:
            return self.metadata.title
        return self.original_filename
