"""
API Router Aggregation.

Combines all v1 routes into a single router.
"""

from fastapi import APIRouter

from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.workspaces import router as workspaces_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(documents_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(workspaces_router)
