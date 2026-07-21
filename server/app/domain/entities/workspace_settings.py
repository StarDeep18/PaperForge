from dataclasses import dataclass, field
from datetime import datetime
import uuid
from app.core.security import utc_now

@dataclass
class WorkspaceSettings:
    """
    Workspace Settings domain entity representing active document selections and themes.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    theme: str = "light"
    selected_document_ids: list[str] = field(default_factory=list)
    active_document_id: str = ""
    active_conversation_id: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
