"""
Conversation and Message Entities.

Represents a chat conversation and its messages within PaperForge.
Conversations are scoped to documents or collections.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.core.security import utc_now


class ConversationScope(str, Enum):
    """What the conversation is about."""

    DOCUMENT = "document"        # Chat with a single paper
    COLLECTION = "collection"    # Chat across a collection
    MULTI_DOCUMENT = "multi_document"  # Chat across selected papers


class MessageRole(str, Enum):
    """Who sent the message."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Citation:
    """
    A source citation within an assistant message.

    Links a specific claim in the response back to the source
    document, page, and text chunk.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    document_title: str = ""
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_text: str = ""
    relevance_score: float = 0.0

    @property
    def display_label(self) -> str:
        """Human-readable citation label."""
        parts = [self.document_title]
        if self.page_number:
            parts.append(f"p.{self.page_number}")
        if self.section:
            parts.append(self.section)
        return ", ".join(parts)


@dataclass
class Message:
    """
    A single message in a conversation.

    Assistant messages may include citations linking claims
    to source documents.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    role: MessageRole = MessageRole.USER
    content: str = ""
    citations: list[Citation] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_user(self) -> bool:
        return self.role == MessageRole.USER

    @property
    def is_assistant(self) -> bool:
        return self.role == MessageRole.ASSISTANT


@dataclass
class Conversation:
    """
    A chat conversation scoped to document(s) or a collection.

    Tracks the full message history for context-aware responses.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = "New Conversation"
    scope: ConversationScope = ConversationScope.DOCUMENT
    document_ids: list[str] = field(default_factory=list)
    collection_id: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def add_message(self, message: Message) -> None:
        """Append a message and update the conversation timestamp."""
        message.conversation_id = self.id
        self.messages.append(message)
        self.updated_at = utc_now()

        # Auto-title from first user message
        if len(self.messages) == 1 and message.is_user:
            self.title = message.content[:80].strip()
            if len(message.content) > 80:
                self.title += "..."

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None

    def get_context_window(self, max_messages: int = 20) -> list[Message]:
        """
        Return recent messages for LLM context.

        Limits to the most recent N messages to stay within
        token limits while maintaining conversation coherence.
        """
        return self.messages[-max_messages:]
