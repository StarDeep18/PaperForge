from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from app.api.dependencies import CurrentUser, get_timeline_event_repo
from app.domain.entities.timeline_event import TimelineEvent
from app.infrastructure.repositories.sqlite_timeline_event_repo import SQLiteTimelineEventRepository

router = APIRouter(prefix="/timeline", tags=["Timeline"])

# ── Schemas ───────────────────────────────────────────────────────

class TimelineEventCreateSchema(BaseModel):
    type: str  # upload, insight_save, ask_question, export_notes
    message: str

class TimelineEventResponseSchema(BaseModel):
    id: str
    type: str
    message: str
    timestamp: datetime

# ── Endpoints ─────────────────────────────────────────────────────

@router.get("", response_model=list[TimelineEventResponseSchema])
async def list_timeline_events(
    current_user: CurrentUser,
    repo: Annotated[SQLiteTimelineEventRepository, Depends(get_timeline_event_repo)],
    limit: int = 50,
):
    """Retrieve logged timeline events for the user."""
    events = await repo.get_all_by_user(current_user.id, limit=limit)
    return [
        TimelineEventResponseSchema(
            id=e.id,
            type=e.type,
            message=e.message,
            timestamp=e.timestamp,
        )
        for e in events
    ]

@router.post("", response_model=TimelineEventResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_timeline_event(
    payload: TimelineEventCreateSchema,
    current_user: CurrentUser,
    repo: Annotated[SQLiteTimelineEventRepository, Depends(get_timeline_event_repo)],
):
    """Log a new timeline action event for the user."""
    event = TimelineEvent(
        user_id=current_user.id,
        type=payload.type,
        message=payload.message,
    )
    saved = await repo.create(event)
    return TimelineEventResponseSchema(
        id=saved.id,
        type=saved.type,
        message=saved.message,
        timestamp=saved.timestamp,
    )
