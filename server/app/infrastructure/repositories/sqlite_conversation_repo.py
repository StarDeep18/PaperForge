"""
SQLite Conversation Repository.

Concrete implementation of ConversationRepository using SQLAlchemy.
Handles both conversations and their messages with citation data.
"""

from typing import Optional
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.conversation import (
    Citation,
    Conversation,
    ConversationScope,
    Message,
    MessageRole,
)
from app.domain.repositories.conversation_repository import ConversationRepository
from app.infrastructure.database.models import ConversationModel, MessageModel


class SQLiteConversationRepository(ConversationRepository):
    """SQLAlchemy-based conversation repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        model = self._conversation_to_model(conversation)
        self._session.add(model)
        await self._session.flush()
        return conversation

    async def get_by_id(
        self, conversation_id: str, user_id: str
    ) -> Optional[Conversation]:
        stmt = (
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._conversation_to_entity(model) if model else None

    async def get_all(
        self,
        user_id: str,
        document_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        stmt = select(ConversationModel).where(ConversationModel.user_id == user_id)

        if document_id:
            # Filter conversations that include this document_id in their document_ids JSON
            stmt = stmt.where(
                ConversationModel.document_ids.contains(document_id)
            )
        if collection_id:
            stmt = stmt.where(ConversationModel.collection_id == collection_id)

        stmt = stmt.order_by(ConversationModel.updated_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        # Return conversations without messages for list view
        return [self._conversation_to_entity(m, include_messages=False) for m in models]

    async def add_message(self, message: Message) -> Message:
        model = self._message_to_model(message)
        self._session.add(model)
        await self._session.flush()
        return message

    async def update(self, conversation: Conversation) -> Conversation:
        stmt = select(ConversationModel).where(ConversationModel.id == conversation.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.title = conversation.title
            model.document_ids = conversation.document_ids
            model.collection_id = conversation.collection_id
            model.updated_at = conversation.updated_at
            await self._session.flush()

        return conversation

    async def delete(self, conversation_id: str, user_id: str) -> bool:
        stmt = select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    # ── Mapping ──────────────────────────────────────────────────

    def _conversation_to_model(self, entity: Conversation) -> ConversationModel:
        return ConversationModel(
            id=entity.id,
            user_id=entity.user_id,
            title=entity.title,
            scope=entity.scope,
            document_ids=entity.document_ids,
            collection_id=entity.collection_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _conversation_to_entity(
        self, model: ConversationModel, include_messages: bool = True
    ) -> Conversation:
        messages = []
        if include_messages and hasattr(model, "messages") and model.messages:
            messages = [self._message_to_entity(m) for m in model.messages]

        return Conversation(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            scope=model.scope or ConversationScope.DOCUMENT,
            document_ids=model.document_ids or [],
            collection_id=model.collection_id,
            messages=messages,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _message_to_model(self, entity: Message) -> MessageModel:
        citations_data = None
        if entity.citations:
            citations_data = [
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "document_title": c.document_title,
                    "page_number": c.page_number,
                    "section": c.section,
                    "chunk_text": c.chunk_text,
                    "relevance_score": c.relevance_score,
                }
                for c in entity.citations
            ]

        return MessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            role=entity.role,
            content=entity.content,
            citations=citations_data,
            created_at=entity.created_at,
        )

    def _message_to_entity(self, model: MessageModel) -> Message:
        citations = []
        if model.citations:
            citations = [
                Citation(
                    id=c.get("id", ""),
                    document_id=c.get("document_id", ""),
                    document_title=c.get("document_title", ""),
                    page_number=c.get("page_number"),
                    section=c.get("section"),
                    chunk_text=c.get("chunk_text", ""),
                    relevance_score=c.get("relevance_score", 0.0),
                )
                for c in model.citations
            ]

        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            role=model.role or MessageRole.USER,
            content=model.content,
            citations=citations,
            created_at=model.created_at,
        )
