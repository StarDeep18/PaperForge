from pydantic import BaseModel
from typing import Optional, Dict

class UserSyncRequest(BaseModel):
    """Payload to synchronize Firebase details with local tenant mapping."""
    email: str
    display_name: Optional[str] = None

class UserResponse(BaseModel):
    """Serialized User profile representation."""
    id: str
    email: str
    display_name: str

class ProfileStatistics(BaseModel):
    workspace_name: str = "Default Workspace"
    storage_used_bytes: int = 0
    storage_used_formatted: str = "0 KB"
    documents_count: int = 0
    questions_asked_count: int = 0
    notes_saved_count: int = 0
    research_sessions_count: int = 0
    last_login: Optional[str] = None

class UserMeResponse(BaseModel):
    """User representation enriched with research workspace statistics."""
    email: str
    display_name: str
    statistics: ProfileStatistics
