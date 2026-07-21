from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.workspace_settings import WorkspaceSettings
from app.domain.repositories.workspace_settings_repository import WorkspaceSettingsRepository
from app.infrastructure.database.models import WorkspaceSettingsModel

class SQLiteWorkspaceSettingsRepository(WorkspaceSettingsRepository):
    """SQLAlchemy-based workspace settings repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        model = WorkspaceSettingsModel(
            id=settings.id,
            user_id=settings.user_id,
            theme=settings.theme,
            selected_document_ids=settings.selected_document_ids,
            active_document_id=settings.active_document_id,
            active_conversation_id=settings.active_conversation_id,
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return settings

    async def get_by_user(self, user_id: str) -> Optional[WorkspaceSettings]:
        stmt = select(WorkspaceSettingsModel).where(WorkspaceSettingsModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        stmt = select(WorkspaceSettingsModel).where(
            WorkspaceSettingsModel.id == settings.id,
            WorkspaceSettingsModel.user_id == settings.user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.theme = settings.theme
            model.selected_document_ids = settings.selected_document_ids
            model.active_document_id = settings.active_document_id
            model.active_conversation_id = settings.active_conversation_id
            model.updated_at = settings.updated_at
            await self._session.flush()
        return settings

    def _to_entity(self, model: WorkspaceSettingsModel) -> WorkspaceSettings:
        return WorkspaceSettings(
            id=model.id,
            user_id=model.user_id,
            theme=model.theme,
            selected_document_ids=model.selected_document_ids or [],
            active_document_id=model.active_document_id or "",
            active_conversation_id=model.active_conversation_id or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
