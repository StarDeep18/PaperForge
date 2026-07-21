from abc import ABC, abstractmethod
from app.domain.entities.timeline_event import TimelineEvent

class TimelineEventRepository(ABC):
    """Interface for timeline event persistence operations."""

    @abstractmethod
    async def create(self, event: TimelineEvent) -> TimelineEvent:
        """Persist a timeline event."""
        ...

    @abstractmethod
    async def get_all_by_user(self, user_id: str, limit: int = 50) -> list[TimelineEvent]:
        """Retrieve timeline events logged for a specific user."""
        ...
