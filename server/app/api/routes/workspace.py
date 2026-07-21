from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.dependencies import CurrentUser, get_workspace_settings_repo
from app.domain.entities.workspace_settings import WorkspaceSettings
from app.infrastructure.repositories.sqlite_workspace_settings_repo import SQLiteWorkspaceSettingsRepository

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

# ── Schemas ───────────────────────────────────────────────────────

class WorkspaceSettingsSchema(BaseModel):
    theme: str
    selected_document_ids: list[str]
    active_document_id: str
    active_conversation_id: str

# ── Endpoints ─────────────────────────────────────────────────────

@router.get(
    "",
    summary="List workspaces",
    description="List all workspaces scoped for the current user.",
)
async def list_workspaces():
    return []

@router.get("/settings", response_model=WorkspaceSettingsSchema)
async def get_settings(
    current_user: CurrentUser,
    repo: Annotated[SQLiteWorkspaceSettingsRepository, Depends(get_workspace_settings_repo)],
):
    """Retrieve workspace settings configuration (theme, selection lists, focus files)."""
    settings = await repo.get_by_user(current_user.id)
    if not settings:
        # Create and return default settings
        settings = WorkspaceSettings(
            user_id=current_user.id,
            theme="light",
            selected_document_ids=[],
            active_document_id="",
            active_conversation_id="",
        )
        await repo.create(settings)
    
    return WorkspaceSettingsSchema(
        theme=settings.theme,
        selected_document_ids=settings.selected_document_ids,
        active_document_id=settings.active_document_id,
        active_conversation_id=settings.active_conversation_id,
    )

@router.put("/settings", response_model=WorkspaceSettingsSchema)
async def update_settings(
    payload: WorkspaceSettingsSchema,
    current_user: CurrentUser,
    repo: Annotated[SQLiteWorkspaceSettingsRepository, Depends(get_workspace_settings_repo)],
):
    """Save/update current workspace settings."""
    settings = await repo.get_by_user(current_user.id)
    if not settings:
        settings = WorkspaceSettings(
            user_id=current_user.id,
            theme=payload.theme,
            selected_document_ids=payload.selected_document_ids,
            active_document_id=payload.active_document_id,
            active_conversation_id=payload.active_conversation_id,
        )
        await repo.create(settings)
    else:
        settings.theme = payload.theme
        settings.selected_document_ids = payload.selected_document_ids
        settings.active_document_id = payload.active_document_id
        settings.active_conversation_id = payload.active_conversation_id
        await repo.update(settings)
        
    return WorkspaceSettingsSchema(
        theme=settings.theme,
        selected_document_ids=settings.selected_document_ids,
        active_document_id=settings.active_document_id,
        active_conversation_id=settings.active_conversation_id,
    )
