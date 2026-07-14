"""
Collection Entity.

Represents a user-created folder/group for organizing research papers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.core.security import utc_now


@dataclass
class Collection:
    """
    A named collection of research papers.

    Collections enable users to organize papers by topic, project,
    course, or any other grouping. A paper can belong to one collection
    (or none). Collections support scoped chat — asking questions
    across all papers in a collection.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    description: Optional[str] = None
    color: str = "#6366f1"  # Default indigo
    icon: str = "folder"
    document_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.updated_at = utc_now()

    def update_description(self, description: str) -> None:
        self.description = description
        self.updated_at = utc_now()

    def increment_document_count(self) -> None:
        self.document_count += 1
        self.updated_at = utc_now()

    def decrement_document_count(self) -> None:
        self.document_count = max(0, self.document_count - 1)
        self.updated_at = utc_now()
