"""
Pydantic Schemas for Documents API.

Request/Response DTOs separate from domain entities.
These define the HTTP contract — validated input and structured output.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Response Schemas ─────────────────────────────────────────────


class DocumentMetadataResponse(BaseModel):
    """Document metadata in API responses."""

    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    page_count: int = 0
    word_count: int = 0


class DocumentResponse(BaseModel):
    """Full document response."""

    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str
    metadata: DocumentMetadataResponse
    collection_id: Optional[str] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseModel):
    """Response after successful upload."""

    id: str
    filename: str
    status: str
    message: str = "Document uploaded successfully. Processing will begin shortly."


# ── Request Schemas ──────────────────────────────────────────────


class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata."""

    collection_id: Optional[str] = None
