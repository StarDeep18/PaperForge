"""
Pydantic Schemas for Chat API.

Request/Response DTOs for the chat interface.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    """A source citation in an assistant message."""

    id: str
    document_id: str
    document_title: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_text: str = ""
    relevance_score: float = 0.0


class MessageResponse(BaseModel):
    """A single chat message."""

    id: str
    role: str
    content: str
    citations: list[CitationResponse] = Field(default_factory=list)
    created_at: datetime


class ConversationResponse(BaseModel):
    """A chat conversation with messages."""

    id: str
    title: str
    scope: str
    document_ids: list[str] = Field(default_factory=list)
    collection_id: Optional[str] = None
    messages: list[MessageResponse] = Field(default_factory=list)
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """List of conversations (without messages)."""

    conversations: list[ConversationResponse]


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None
    document_ids: Optional[list[str]] = None
    collection_id: Optional[str] = None
    stream: bool = False


class SendMessageResponse(BaseModel):
    """Response to a sent message (non-streaming)."""

    conversation_id: str
    message: MessageResponse
    citations: list[CitationResponse] = Field(default_factory=list)
