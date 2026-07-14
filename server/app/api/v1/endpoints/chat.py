"""
Chat API Endpoints.

Handles sending messages, retrieving conversations, and streaming responses.
"""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    CurrentUserId,
    get_conversation_repo,
    get_send_message_use_case,
)
from app.api.v1.schemas.chat import (
    CitationResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.application.chat.send_message import SendMessageUseCase
from app.domain.entities.conversation import Conversation, Message
from app.domain.exceptions import ConversationNotFoundError
from app.infrastructure.repositories.sqlite_conversation_repo import SQLiteConversationRepository

router = APIRouter(prefix="/chat", tags=["Chat"])


def _message_to_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        role=msg.role.value,
        content=msg.content,
        citations=[
            CitationResponse(
                id=c.id,
                document_id=c.document_id,
                document_title=c.document_title,
                page_number=c.page_number,
                section=c.section,
                chunk_text=c.chunk_text,
                relevance_score=c.relevance_score,
            )
            for c in msg.citations
        ],
        created_at=msg.created_at,
    )


def _conversation_to_response(conv: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        scope=conv.scope.value,
        document_ids=conv.document_ids,
        collection_id=conv.collection_id,
        messages=[_message_to_response(m) for m in conv.messages],
        message_count=conv.message_count,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post(
    "/send",
    response_model=SendMessageResponse,
    summary="Send a message",
)
async def send_message(
    request: SendMessageRequest,
    user_id: str = Depends(CurrentUserId),
    use_case: SendMessageUseCase = Depends(get_send_message_use_case),
):
    """
    Send a message and receive a RAG-powered, citation-aware response.

    If no conversation_id is provided, a new conversation is created.
    You must provide either document_ids or collection_id to scope the search.
    """
    if request.stream:
        # For streaming, redirect to the stream endpoint
        return await send_message_stream(request, user_id, use_case)

    try:
        message, conversation = await use_case.execute(
            user_id=user_id,
            message_content=request.message,
            conversation_id=request.conversation_id,
            document_ids=request.document_ids,
            collection_id=request.collection_id,
        )

        return SendMessageResponse(
            conversation_id=conversation.id,
            message=_message_to_response(message),
            citations=[
                CitationResponse(
                    id=c.id,
                    document_id=c.document_id,
                    document_title=c.document_title,
                    page_number=c.page_number,
                    section=c.section,
                    chunk_text=c.chunk_text,
                    relevance_score=c.relevance_score,
                )
                for c in message.citations
            ],
        )

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.post(
    "/send/stream",
    summary="Send a message with streaming response",
)
async def send_message_stream(
    request: SendMessageRequest,
    user_id: str = Depends(CurrentUserId),
    use_case: SendMessageUseCase = Depends(get_send_message_use_case),
):
    """
    Send a message and stream the response using Server-Sent Events.

    Events:
    - `citations`: Sent first with the retrieved source citations
    - `token`: Streamed response tokens
    - `done`: Sent when the response is complete
    - `error`: Sent if an error occurs
    """
    try:
        stream, citations, conversation = await use_case.execute_stream(
            user_id=user_id,
            message_content=request.message,
            conversation_id=request.conversation_id,
            document_ids=request.document_ids,
            collection_id=request.collection_id,
        )

        async def event_generator():
            full_response = ""

            # Send citations first
            citations_data = [
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "document_title": c.document_title,
                    "page_number": c.page_number,
                    "section": c.section,
                    "chunk_text": c.chunk_text[:200],
                    "relevance_score": c.relevance_score,
                }
                for c in citations
            ]
            yield f"event: citations\ndata: {json.dumps(citations_data)}\n\n"

            # Stream response tokens
            try:
                async for token in stream:
                    full_response += token
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

                # Save the complete response
                await use_case.save_streamed_response(
                    conversation=conversation,
                    response_text=full_response,
                    citations=citations,
                )

                yield f"event: done\ndata: {json.dumps({'conversation_id': conversation.id})}\n\n"

            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
)
async def list_conversations(
    user_id: str = Depends(CurrentUserId),
    document_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """List all conversations, optionally filtered by document or collection."""
    conversations = await conversation_repo.get_all(
        user_id=user_id,
        document_id=document_id,
        collection_id=collection_id,
    )
    return ConversationListResponse(
        conversations=[_conversation_to_response(c) for c in conversations]
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation",
)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(CurrentUserId),
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """Retrieve a conversation with all its messages."""
    conversation = await conversation_repo.get_by_id(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_to_response(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Delete conversation",
)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(CurrentUserId),
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """Delete a conversation and all its messages."""
    deleted = await conversation_repo.delete(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None
