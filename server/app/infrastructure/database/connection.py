"""
Database Connection & Session Management.

Provides async SQLAlchemy engine, session factory, and a
dependency-injection-friendly session generator for FastAPI.

Designed to work with SQLite (dev) and PostgreSQL (production)
by changing only the DATABASE_URL environment variable.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator

from app.core.config import get_settings


settings = get_settings()

# ── Engine ───────────────────────────────────────────────────────
# SQLite requires check_same_thread=False for async usage.
# PostgreSQL doesn't need this, so we detect the driver.

connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# ── Session Factory ──────────────────────────────────────────────

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage in endpoints:
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...

    The session is automatically closed after the request completes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
