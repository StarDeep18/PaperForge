"""
SQLAlchemy ORM Models.

These are the database table definitions — separate from domain entities.
Domain entities are pure Python dataclasses (no ORM coupling).
These ORM models handle persistence and are mapped to/from domain entities
in the repository implementations.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.security import utc_now
from app.domain.entities.document import DocumentStatus, DocumentType
from app.domain.entities.conversation import ConversationScope, MessageRole


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class UserModel(Base):
    """Users table."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    firebase_uid = Column(String(128), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(512), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    documents = relationship("DocumentModel", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("CollectionModel", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("ConversationModel", back_populates="user", cascade="all, delete-orphan")


class CollectionModel(Base):
    """Collections table — organizing groups of papers."""

    __tablename__ = "collections"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")
    icon = Column(String(50), default="folder")
    document_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("UserModel", back_populates="collections")
    documents = relationship("DocumentModel", back_populates="collection")


class DocumentModel(Base):
    """Documents table — uploaded research papers."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    collection_id = Column(String(36), ForeignKey("collections.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(Enum(DocumentType), default=DocumentType.PDF)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, index=True)

    # Metadata (stored as JSON for flexibility)
    title = Column(String(512), nullable=True)
    authors = Column(JSON, nullable=True)  # list[str]
    abstract = Column(Text, nullable=True)
    publication_date = Column(String(50), nullable=True)
    journal = Column(String(255), nullable=True)
    doi = Column(String(255), nullable=True)
    keywords = Column(JSON, nullable=True)  # list[str]
    page_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)

    raw_text = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("UserModel", back_populates="documents")
    collection = relationship("CollectionModel", back_populates="documents")
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")


class ChunkModel(Base):
    """Chunks table — text fragments for RAG retrieval."""

    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_content = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    section_header = Column(String(255), nullable=True)
    chunk_index = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    document = relationship("DocumentModel", back_populates="chunks")


class ConversationModel(Base):
    """Conversations table — chat sessions."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="New Conversation")
    scope = Column(Enum(ConversationScope), default=ConversationScope.DOCUMENT)
    document_ids = Column(JSON, nullable=True)  # list[str]
    collection_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("UserModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan", order_by="MessageModel.created_at")


class MessageModel(Base):
    """Messages table — individual chat messages."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)  # list[dict] — serialized Citation objects
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")


class ResearchNoteModel(Base):
    """Research notes saved by the user."""

    __tablename__ = "research_notes"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    document_title = Column(String(512), nullable=False)
    page_number = Column(Integer, default=1)
    snippet = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("UserModel")
    document = relationship("DocumentModel")


class TimelineEventModel(Base):
    """Timeline events representing research session logs."""

    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utc_now)

    user = relationship("UserModel")


class WorkspaceSettingsModel(Base):
    """Workspace settings representing active session state."""

    __tablename__ = "workspace_settings"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    theme = Column(String(20), default="light")
    selected_document_ids = Column(JSON, nullable=True)  # list[str]
    active_document_id = Column(String(36), nullable=True)
    active_conversation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("UserModel")
