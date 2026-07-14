"""
Document Repository Interface.

Abstract base class defining the contract for document persistence.
Implementations may use SQLite, PostgreSQL, or any other storage backend.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.document import Document


class DocumentRepository(ABC):
    """Abstract interface for document persistence operations."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new document."""
        ...

    @abstractmethod
    async def get_by_id(self, document_id: str, user_id: str) -> Optional[Document]:
        """Retrieve a document by ID, scoped to user."""
        ...

    @abstractmethod
    async def get_all(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """List documents for a user, optionally filtered by collection."""
        ...

    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Update an existing document."""
        ...

    @abstractmethod
    async def delete(self, document_id: str, user_id: str) -> bool:
        """Delete a document. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def count(self, user_id: str, collection_id: Optional[str] = None) -> int:
        """Count documents for a user, optionally in a collection."""
        ...

    @abstractmethod
    async def get_by_ids(self, document_ids: list[str], user_id: str) -> list[Document]:
        """Retrieve multiple documents by their IDs."""
        ...
