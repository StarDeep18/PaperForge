from typing import Annotated
from fastapi import APIRouter, Depends
from app.api.dependencies import (
    CurrentUser,
    get_document_repo,
    get_research_note_repo,
    get_timeline_event_repo,
)
from app.api.schemas.auth import UserResponse, UserMeResponse, UserSyncRequest
from app.infrastructure.repositories.sqlite_document_repo import SQLiteDocumentRepository
from app.infrastructure.repositories.sqlite_research_note_repo import SQLiteResearchNoteRepository
from app.infrastructure.repositories.sqlite_timeline_event_repo import SQLiteTimelineEventRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/sync", response_model=UserResponse)
async def sync_user(
    current_user: CurrentUser,
):
    """
    Synchronizes the authenticated Firebase user with the local SQL database.
    Creates a new user record or updates email/display name details.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
    )

@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: CurrentUser,
    document_repo: Annotated[SQLiteDocumentRepository, Depends(get_document_repo)],
    research_note_repo: Annotated[SQLiteResearchNoteRepository, Depends(get_research_note_repo)],
    timeline_event_repo: Annotated[SQLiteTimelineEventRepository, Depends(get_timeline_event_repo)],
):
    """
    Returns the currently logged-in user profile along with active research workspace statistics.
    """
    docs_count = await document_repo.count(current_user.id)
    notes = await research_note_repo.get_all_by_user(current_user.id)
    events = await timeline_event_repo.get_all_by_user(current_user.id)

    return UserMeResponse(
        email=current_user.email,
        display_name=current_user.display_name,
        statistics={
            "documents_count": docs_count,
            "notes_count": len(notes),
            "timeline_events_count": len(events),
        },
    )
