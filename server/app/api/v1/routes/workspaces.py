"""
API v1 Workspaces Router.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get(
    "",
    summary="List workspaces",
    description="List all workspaces scoped for the current user.",
)
async def list_workspaces():
    return []
