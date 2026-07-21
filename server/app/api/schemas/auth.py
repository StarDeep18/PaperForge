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

class UserMeResponse(BaseModel):
    """User representation enriched with research usage statistics."""
    email: str
    display_name: str
    statistics: Dict[str, int]
