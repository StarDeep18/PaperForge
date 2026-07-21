from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel

class SQLiteUserRepository(UserRepository):
    """SQLAlchemy-based user repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            firebase_uid=user.firebase_uid,
            email=user.email,
            name=user.display_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.firebase_uid == firebase_uid)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.email = user.email
            model.name = user.display_name
            model.firebase_uid = user.firebase_uid
            model.updated_at = user.updated_at
            await self._session.flush()
        return user

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            firebase_uid=getattr(model, "firebase_uid", "") or "",
            email=model.email,
            display_name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
