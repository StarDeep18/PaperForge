from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.timeline_event import TimelineEvent
from app.domain.repositories.timeline_event_repository import TimelineEventRepository
from app.infrastructure.database.models import TimelineEventModel

class SQLiteTimelineEventRepository(TimelineEventRepository):
    """SQLAlchemy-based timeline event repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, event: TimelineEvent) -> TimelineEvent:
        model = TimelineEventModel(
            id=event.id,
            user_id=event.user_id,
            type=event.type,
            message=event.message,
            timestamp=event.timestamp,
        )
        self._session.add(model)
        await self._session.flush()
        return event

    async def get_all_by_user(self, user_id: str, limit: int = 50) -> list[TimelineEvent]:
        stmt = select(TimelineEventModel).where(
            TimelineEventModel.user_id == user_id
        ).order_by(TimelineEventModel.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: TimelineEventModel) -> TimelineEvent:
        return TimelineEvent(
            id=model.id,
            user_id=model.user_id,
            type=model.type,
            message=model.message,
            timestamp=model.timestamp,
        )
