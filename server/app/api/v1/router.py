"""
API Router Aggregation.

Combines all v1 endpoint routers into a single router
that is mounted in the FastAPI application.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.collections import router as collections_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(documents_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(collections_router)
