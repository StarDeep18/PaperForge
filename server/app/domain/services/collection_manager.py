"""
Collection Manager Interface.

Defines the interface for managing collections/indexes in the vector database.
"""

from abc import ABC, abstractmethod
from typing import Optional


class CollectionManager(ABC):
    """
    Interface for vector database collection lifecycle operations.
    
    Decoupled from VectorStoreService, which solely manages vector operations.
    """

    @abstractmethod
    async def create_collection(self, name: str, metadata: Optional[dict] = None) -> None:
        """
        Create a new collection in the vector database.

        Args:
            name: Name of the collection.
            metadata: Optional configuration/metadata dict.
        """
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """
        Delete a collection from the vector database.

        Args:
            name: Name of the collection.
        """
        pass

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """
        List all collection names in the vector database.

        Returns:
            List of collection names.
        """
        pass

    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            name: Name of the collection.

        Returns:
            True if exists, False otherwise.
        """
        pass

    @abstractmethod
    async def get_collection_stats(self, name: str) -> dict:
        """
        Retrieve statistics (e.g., total document count, index size) for a collection.

        Args:
            name: Name of the collection.

        Returns:
            Dictionary containing collection metrics.
        """
        pass
