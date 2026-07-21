from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models.user import User

class UserRepository(ABC):
    """Interface for user persistence operations."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user record."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by their local ID."""
        ...

    @abstractmethod
    async def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Retrieve a user by their Firebase UID."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user record."""
        ...
