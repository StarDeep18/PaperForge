from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.dependencies import CurrentUser, get_research_note_repo
from app.domain.entities.research_note import ResearchNote
from app.infrastructure.repositories.sqlite_research_note_repo import SQLiteResearchNoteRepository

router = APIRouter(prefix="/notes", tags=["Research Notes"])

# ── Schemas ───────────────────────────────────────────────────────

class ResearchNoteCreateSchema(BaseModel):
    document_id: str
    document_title: str
    page_number: int
    snippet: str
    note: str

class ResearchNoteUpdateSchema(BaseModel):
    note: str

class ResearchNoteResponseSchema(BaseModel):
    id: str
    document_id: str
    document_title: str
    page_number: int
    snippet: str
    note: str
    created_at: datetime
    updated_at: datetime

# ── Endpoints ─────────────────────────────────────────────────────

@router.get("", response_model=list[ResearchNoteResponseSchema])
async def list_notes(
    current_user: CurrentUser,
    repo: Annotated[SQLiteResearchNoteRepository, Depends(get_research_note_repo)],
    document_id: Optional[str] = None,
):
    """List all research notes for the authenticated user, optionally filtered by document_id."""
    if document_id:
        notes = await repo.get_by_document(document_id, current_user.id)
    else:
        notes = await repo.get_all_by_user(current_user.id)
    
    return [
        ResearchNoteResponseSchema(
            id=n.id,
            document_id=n.document_id,
            document_title=n.document_title,
            page_number=n.page_number,
            snippet=n.snippet,
            note=n.note,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]

@router.post("", response_model=ResearchNoteResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: ResearchNoteCreateSchema,
    current_user: CurrentUser,
    repo: Annotated[SQLiteResearchNoteRepository, Depends(get_research_note_repo)],
):
    """Create a new research note scoped to the current user."""
    note = ResearchNote(
        user_id=current_user.id,
        document_id=payload.document_id,
        document_title=payload.document_title,
        page_number=payload.page_number,
        snippet=payload.snippet,
        note=payload.note,
    )
    saved = await repo.create(note)
    return ResearchNoteResponseSchema(
        id=saved.id,
        document_id=saved.document_id,
        document_title=saved.document_title,
        page_number=saved.page_number,
        snippet=saved.snippet,
        note=saved.note,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )

@router.patch("/{note_id}", response_model=ResearchNoteResponseSchema)
async def update_note(
    note_id: str,
    payload: ResearchNoteUpdateSchema,
    current_user: CurrentUser,
    repo: Annotated[SQLiteResearchNoteRepository, Depends(get_research_note_repo)],
):
    """Update note comments/annotations."""
    note = await repo.get_by_id(note_id, current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research note not found or access denied.",
        )
    
    note.note = payload.note
    updated = await repo.update(note)
    return ResearchNoteResponseSchema(
        id=updated.id,
        document_id=updated.document_id,
        document_title=updated.document_title,
        page_number=updated.page_number,
        snippet=updated.snippet,
        note=updated.note,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: CurrentUser,
    repo: Annotated[SQLiteResearchNoteRepository, Depends(get_research_note_repo)],
):
    """Delete a research note."""
    success = await repo.delete(note_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research note not found or access denied.",
        )
    return None
