"""
User Entity.

Represents a user of the PaperForge platform.
Auth-ready design — currently uses a default dev user.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.core.security import utc_now


@dataclass
class User:
    """
    User entity for multi-tenant scoping.

    All resources (documents, collections, conversations) are
    scoped to a user_id for future multi-user support.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    name: str = ""
    avatar_url: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
