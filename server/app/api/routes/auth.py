from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.api.dependencies import (
    CurrentUser,
    get_document_repo,
    get_research_note_repo,
    get_timeline_event_repo,
)
from app.api.schemas.auth import UserResponse, UserMeResponse, ProfileStatistics
from app.infrastructure.repositories.sqlite_document_repo import SQLiteDocumentRepository
from app.infrastructure.repositories.sqlite_research_note_repo import SQLiteResearchNoteRepository
from app.infrastructure.repositories.sqlite_timeline_event_repo import SQLiteTimelineEventRepository
from app.infrastructure.database.connection import async_session_factory
from app.infrastructure.database.models import DocumentModel, ConversationModel, MessageModel
from app.domain.entities.conversation import MessageRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _format_bytes(bytes_num: int) -> str:
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_num / (1024 * 1024 * 1024):.2f} GB"


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

    async with async_session_factory() as session:
        # Sum file size of user documents
        storage_res = await session.execute(
            select(func.coalesce(func.sum(DocumentModel.file_size), 0)).where(DocumentModel.user_id == current_user.id)
        )
        storage_bytes = int(storage_res.scalar_one_or_none() or 0)

        # Count conversations
        conv_res = await session.execute(
            select(func.count(ConversationModel.id)).where(ConversationModel.user_id == current_user.id)
        )
        sessions_count = int(conv_res.scalar_one_or_none() or 0)

        # Count user questions asked
        q_res = await session.execute(
            select(func.count(MessageModel.id))
            .join(ConversationModel, MessageModel.conversation_id == ConversationModel.id)
            .where(ConversationModel.user_id == current_user.id)
            .where(MessageModel.role == MessageRole.USER)
        )
        questions_count = int(q_res.scalar_one_or_none() or 0)

    last_login_iso = datetime.now().isoformat()

    return UserMeResponse(
        email=current_user.email,
        display_name=current_user.display_name,
        statistics=ProfileStatistics(
            workspace_name="Primary Research Workspace",
            storage_used_bytes=storage_bytes,
            storage_used_formatted=_format_bytes(storage_bytes),
            documents_count=docs_count,
            questions_asked_count=questions_count,
            notes_saved_count=len(notes),
            research_sessions_count=sessions_count,
            last_login=last_login_iso,
        ),
    )
