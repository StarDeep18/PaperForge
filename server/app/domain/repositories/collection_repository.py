"""
Collection Repository Interface.

Abstract base class for collection persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.collection import Collection


class CollectionRepository(ABC):
    """Abstract interface for collection persistence operations."""

    @abstractmethod
    async def create(self, collection: Collection) -> Collection:
        """Persist a new collection."""
        ...

    @abstractmethod
    async def get_by_id(self, collection_id: str, user_id: str) -> Optional[Collection]:
        """Retrieve a collection by ID, scoped to user."""
        ...

    @abstractmethod
    async def get_all(self, user_id: str) -> list[Collection]:
        """List all collections for a user."""
        ...

    @abstractmethod
    async def update(self, collection: Collection) -> Collection:
        """Update an existing collection."""
        ...

    @abstractmethod
    async def delete(self, collection_id: str, user_id: str) -> bool:
        """Delete a collection. Returns True if deleted."""
        ...
