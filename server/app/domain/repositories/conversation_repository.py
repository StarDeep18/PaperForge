"""
Conversation Repository Interface.

Abstract base class for conversation and message persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.conversation import Conversation, Message


class ConversationRepository(ABC):
    """Abstract interface for conversation persistence operations."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation."""
        ...

    @abstractmethod
    async def get_by_id(
        self, conversation_id: str, user_id: str
    ) -> Optional[Conversation]:
        """Retrieve a conversation with its messages."""
        ...

    @abstractmethod
    async def get_all(
        self,
        user_id: str,
        document_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations, optionally filtered by document or collection."""
        ...

    @abstractmethod
    async def add_message(self, message: Message) -> Message:
        """Persist a new message to a conversation."""
        ...

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Update conversation metadata (title, etc.)."""
        ...

    @abstractmethod
    async def delete(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and all its messages."""
        ...
