from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.research_note import ResearchNote

class ResearchNoteRepository(ABC):
    """Interface for research note persistence operations."""

    @abstractmethod
    async def create(self, note: ResearchNote) -> ResearchNote:
        """Persist a new note."""
        ...

    @abstractmethod
    async def get_by_id(self, note_id: str, user_id: str) -> Optional[ResearchNote]:
        """Retrieve a specific note, scoped to user."""
        ...

    @abstractmethod
    async def get_all_by_user(self, user_id: str) -> list[ResearchNote]:
        """Retrieve all notes for a user."""
        ...

    @abstractmethod
    async def get_by_document(self, document_id: str, user_id: str) -> list[ResearchNote]:
        """Retrieve notes associated with a specific document, scoped to user."""
        ...

    @abstractmethod
    async def update(self, note: ResearchNote) -> ResearchNote:
        """Update an existing note."""
        ...

    @abstractmethod
    async def delete(self, note_id: str, user_id: str) -> bool:
        """Delete a note. Returns True if deleted, False if not found."""
        ...
