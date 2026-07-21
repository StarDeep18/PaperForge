from dataclasses import dataclass, field
from datetime import datetime
import uuid
from app.core.security import utc_now

@dataclass
class User:
    """
    Core User domain model for multi-tenant and authentication state mapping.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    firebase_uid: str = ""
    email: str = ""
    display_name: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
