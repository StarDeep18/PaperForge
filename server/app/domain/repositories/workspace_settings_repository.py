from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.workspace_settings import WorkspaceSettings

class WorkspaceSettingsRepository(ABC):
    """Interface for workspace settings persistence operations."""

    @abstractmethod
    async def create(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        """Create initial settings configuration."""
        ...

    @abstractmethod
    async def get_by_user(self, user_id: str) -> Optional[WorkspaceSettings]:
        """Retrieve settings for a user."""
        ...

    @abstractmethod
    async def update(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        """Update existing settings configuration."""
        ...
