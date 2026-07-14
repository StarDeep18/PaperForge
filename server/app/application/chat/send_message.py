"""
Send Message Use Case.

Handles sending a user message in a conversation:
1. Create or retrieve the conversation
2. Save the user message
3. Run RAG pipeline to generate a response
4. Save the assistant message with citations
5. Return the response
"""

from typing import AsyncIterator, Optional

from app.core.logging import logger
from app.domain.entities.conversation import (
    Citation,
    Conversation,
    ConversationScope,
    Message,
    MessageRole,
)
from app.domain.exceptions import ConversationNotFoundError, DocumentNotFoundError
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.ai.rag_chain import RAGChain


class SendMessageUseCase:
    """
    Orchestrates sending a message and generating a RAG response.

    Supports both standard and streaming response modes.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        document_repo: DocumentRepository,
        rag_chain: RAGChain,
    ):
        self._conversation_repo = conversation_repo
        self._document_repo = document_repo
        self._rag_chain = rag_chain

    async def execute(
        self,
        user_id: str,
        message_content: str,
        conversation_id: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
    ) -> tuple[Message, Conversation]:
        """
        Send a message and get a RAG-powered response.

        Args:
            user_id: The user sending the message.
            message_content: The user's question.
            conversation_id: Existing conversation ID, or None to create new.
            document_ids: Document IDs to scope the RAG query.
            collection_id: Collection ID to scope the RAG query.

        Returns:
            Tuple of (assistant_message, conversation).
        """
        # Get or create conversation
        conversation = await self._get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            document_ids=document_ids,
            collection_id=collection_id,
        )

        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message_content,
        )
        conversation.add_message(user_message)
        await self._conversation_repo.add_message(user_message)

        # Build chat history for context
        chat_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in conversation.get_context_window(max_messages=10)
            if msg.id != user_message.id  # Exclude the current message
        ]

        # Run RAG query
        response_text, citations = await self._rag_chain.query(
            question=message_content,
            document_ids=conversation.document_ids,
            collection_id=conversation.collection_id,
            chat_history=chat_history if chat_history else None,
        )

        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            citations=citations,
        )
        conversation.add_message(assistant_message)
        await self._conversation_repo.add_message(assistant_message)

        # Update conversation
        await self._conversation_repo.update(conversation)

        logger.info(
            f"Message processed: conversation={conversation.id}, "
            f"citations={len(citations)}"
        )

        return assistant_message, conversation

    async def execute_stream(
        self,
        user_id: str,
        message_content: str,
        conversation_id: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
    ) -> tuple[AsyncIterator[str], list[Citation], Conversation]:
        """
        Send a message and get a streaming RAG response.

        Returns:
            Tuple of (response_stream, citations, conversation).
            Citations are returned upfront from retrieval.
        """
        conversation = await self._get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            document_ids=document_ids,
            collection_id=collection_id,
        )

        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message_content,
        )
        conversation.add_message(user_message)
        await self._conversation_repo.add_message(user_message)

        # Build chat history
        chat_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in conversation.get_context_window(max_messages=10)
            if msg.id != user_message.id
        ]

        # Get streaming response
        stream, citations = await self._rag_chain.query_stream(
            question=message_content,
            document_ids=conversation.document_ids,
            collection_id=conversation.collection_id,
            chat_history=chat_history if chat_history else None,
        )

        return stream, citations, conversation

    async def save_streamed_response(
        self,
        conversation: Conversation,
        response_text: str,
        citations: list[Citation],
    ) -> Message:
        """Save a streamed response after it completes."""
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            citations=citations,
        )
        conversation.add_message(assistant_message)
        await self._conversation_repo.add_message(assistant_message)
        await self._conversation_repo.update(conversation)
        return assistant_message

    async def _get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str],
        document_ids: Optional[list[str]],
        collection_id: Optional[str],
    ) -> Conversation:
        """Retrieve an existing conversation or create a new one."""
        if conversation_id:
            conversation = await self._conversation_repo.get_by_id(
                conversation_id, user_id
            )
            if not conversation:
                raise ConversationNotFoundError(conversation_id)
            return conversation

        # Determine scope
        if collection_id:
            scope = ConversationScope.COLLECTION
        elif document_ids and len(document_ids) > 1:
            scope = ConversationScope.MULTI_DOCUMENT
        else:
            scope = ConversationScope.DOCUMENT

        conversation = Conversation(
            user_id=user_id,
            scope=scope,
            document_ids=document_ids or [],
            collection_id=collection_id,
        )
        await self._conversation_repo.create(conversation)
        return conversation
