from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.research_note import ResearchNote
from app.domain.repositories.research_note_repository import ResearchNoteRepository
from app.infrastructure.database.models import ResearchNoteModel

class SQLiteResearchNoteRepository(ResearchNoteRepository):
    """SQLAlchemy-based research note repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, note: ResearchNote) -> ResearchNote:
        model = ResearchNoteModel(
            id=note.id,
            user_id=note.user_id,
            document_id=note.document_id,
            document_title=note.document_title,
            page_number=note.page_number,
            snippet=note.snippet,
            note=note.note,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return note

    async def get_by_id(self, note_id: str, user_id: str) -> Optional[ResearchNote]:
        stmt = select(ResearchNoteModel).where(
            ResearchNoteModel.id == note_id,
            ResearchNoteModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all_by_user(self, user_id: str) -> list[ResearchNote]:
        stmt = select(ResearchNoteModel).where(
            ResearchNoteModel.user_id == user_id
        ).order_by(ResearchNoteModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_document(self, document_id: str, user_id: str) -> list[ResearchNote]:
        stmt = select(ResearchNoteModel).where(
            ResearchNoteModel.document_id == document_id,
            ResearchNoteModel.user_id == user_id
        ).order_by(ResearchNoteModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update(self, note: ResearchNote) -> ResearchNote:
        stmt = select(ResearchNoteModel).where(
            ResearchNoteModel.id == note.id,
            ResearchNoteModel.user_id == note.user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.note = note.note
            model.page_number = note.page_number
            model.snippet = note.snippet
            model.updated_at = note.updated_at
            await self._session.flush()
        return note

    async def delete(self, note_id: str, user_id: str) -> bool:
        stmt = select(ResearchNoteModel).where(
            ResearchNoteModel.id == note_id,
            ResearchNoteModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    def _to_entity(self, model: ResearchNoteModel) -> ResearchNote:
        return ResearchNote(
            id=model.id,
            user_id=model.user_id,
            document_id=model.document_id,
            document_title=model.document_title,
            page_number=model.page_number,
            snippet=model.snippet,
            note=model.note or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
