"""
Metadata Filter Model.

Provides an extensible, unified structure for scoping vector search operations.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetadataFilter:
    """
    Extensible filtering criteria for similarity searches.
    
    Supports scoping search by collections, documents, workspaces, authors, tags, and more.
    """

    document_ids: Optional[list[str]] = None
    collection_id: Optional[str] = None
    workspace_id: Optional[str] = None
    tags: Optional[list[str]] = None
    author: Optional[str] = None
    year: Optional[int] = None
    paper_type: Optional[str] = None
    additional_filters: dict = field(default_factory=dict)
