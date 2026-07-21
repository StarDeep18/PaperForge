"""
PaperForge — FastAPI Application Factory.

Creates and configures the FastAPI application instance with:
- CORS middleware
- Error handling middleware
- API routers
- Database initialization
- Startup/shutdown lifecycle events
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import logger
from app.api.router import api_router
from fastapi.middleware.gzip import GZipMiddleware
from app.api.limiter import limiter
from slowapi.errors import RateLimitExceeded
from app.api.middleware import (
    ErrorHandlingMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingAndTimingMiddleware,
)
from app.infrastructure.database.connection import engine
from app.infrastructure.database.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.

    Handles startup (database init) and shutdown (cleanup).
    """
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────
    logger.info(f"🚀 Starting {settings.app_name} ({settings.app_env})")

    # Ensure data directory exists
    settings.data_path
    settings.upload_path

    # Run raw SQL to add firebase_uid column if missing (SQLite development migration)
    async with engine.begin() as conn:
        def migrate_schema(connection):
            cursor = connection.connection.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "firebase_uid" not in columns:
                logger.info("Altering users table to add firebase_uid column...")
                cursor.execute("ALTER TABLE users ADD COLUMN firebase_uid VARCHAR(128)")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_firebase_uid ON users (firebase_uid)")
                connection.connection.commit()
                logger.info("users table altered successfully")
        await conn.run_sync(migrate_schema)

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Create default dev user
    from app.infrastructure.database.connection import async_session_factory
    from app.infrastructure.database.models import UserModel
    from app.core.security import DEFAULT_USER_ID, DEFAULT_USER_EMAIL, DEFAULT_USER_NAME
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.id == DEFAULT_USER_ID)
        )
        if not result.scalar_one_or_none():
            session.add(UserModel(
                id=DEFAULT_USER_ID,
                email=DEFAULT_USER_EMAIL,
                name=DEFAULT_USER_NAME,
            ))
            await session.commit()
            logger.info("Default dev user created")

    logger.info(f"✅ {settings.app_name} ready at http://{settings.server_host}:{settings.server_port}")

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info(f"🛑 Shutting down {settings.app_name}")
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI app.

    This pattern allows creating multiple app instances for testing.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Research Workspace",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingAndTimingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(ErrorHandlingMiddleware)

    # Rate Limiting State & Custom Exception Handler
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        from app.core.logging import request_id_var
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "request_id": request_id_var.get(),
                "details": str(exc),
            },
        )

    # ── Routers ──────────────────────────────────────────────
    app.include_router(api_router)

    # ── Health Check ─────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    # ── Prometheus Metrics ───────────────────────────────────
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=False, tags=["System"])

    return app


# Create the app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
