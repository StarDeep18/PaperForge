"""
SQLite Collection Repository.

Concrete implementation of CollectionRepository using SQLAlchemy.
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.collection import Collection
from app.domain.repositories.collection_repository import CollectionRepository
from app.infrastructure.database.models import CollectionModel


class SQLiteCollectionRepository(CollectionRepository):
    """SQLAlchemy-based collection repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, collection: Collection) -> Collection:
        model = self._to_model(collection)
        self._session.add(model)
        await self._session.flush()
        return collection

    async def get_by_id(self, collection_id: str, user_id: str) -> Optional[Collection]:
        stmt = select(CollectionModel).where(
            CollectionModel.id == collection_id,
            CollectionModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all(self, user_id: str) -> list[Collection]:
        stmt = (
            select(CollectionModel)
            .where(CollectionModel.user_id == user_id)
            .order_by(CollectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update(self, collection: Collection) -> Collection:
        stmt = select(CollectionModel).where(CollectionModel.id == collection.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.name = collection.name
            model.description = collection.description
            model.color = collection.color
            model.icon = collection.icon
            model.document_count = collection.document_count
            model.updated_at = collection.updated_at
            await self._session.flush()

        return collection

    async def delete(self, collection_id: str, user_id: str) -> bool:
        stmt = select(CollectionModel).where(
            CollectionModel.id == collection_id,
            CollectionModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    # ── Mapping ──────────────────────────────────────────────────

    def _to_model(self, entity: Collection) -> CollectionModel:
        return CollectionModel(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name,
            description=entity.description,
            color=entity.color,
            icon=entity.icon,
            document_count=entity.document_count,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_entity(self, model: CollectionModel) -> Collection:
        return Collection(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            color=model.color,
            icon=model.icon,
            document_count=model.document_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
