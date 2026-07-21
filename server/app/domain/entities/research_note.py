from dataclasses import dataclass, field
from datetime import datetime
import uuid
from app.core.security import utc_now

@dataclass
class ResearchNote:
    """
    Research Note domain entity to persist citations annotations and highlights.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    document_id: str = ""
    document_title: str = ""
    page_number: int = 1
    snippet: str = ""
    note: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
