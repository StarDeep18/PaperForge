from dataclasses import dataclass, field
from datetime import datetime
import uuid
from app.core.security import utc_now

@dataclass
class TimelineEvent:
    """
    Timeline Event domain entity representing research session operations.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    type: str = ""  # upload, insight_save, ask_question, export_notes
    message: str = ""
    timestamp: datetime = field(default_factory=utc_now)
