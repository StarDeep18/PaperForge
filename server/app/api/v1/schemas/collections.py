"""
Pydantic Schemas for Collections API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CollectionResponse(BaseModel):
    """Full collection response."""

    id: str
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"
    icon: str = "folder"
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    """List of collections."""

    collections: list[CollectionResponse]


class CreateCollectionRequest(BaseModel):
    """Request to create a new collection."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: str = Field("#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field("folder", max_length=50)


class UpdateCollectionRequest(BaseModel):
    """Request to update a collection."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
