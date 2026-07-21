"""
API Router Aggregation.

Combines all routes into a single router.
"""

from fastapi import APIRouter

from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.workspace import router as workspace_router
from app.api.routes.auth import router as auth_router
from app.api.routes.notes import router as notes_router
from app.api.routes.timeline import router as timeline_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(documents_router)
api_router.include_router(chat_router)
api_router.include_router(health_router)
api_router.include_router(workspace_router)
api_router.include_router(auth_router)
api_router.include_router(notes_router)
api_router.include_router(timeline_router)
