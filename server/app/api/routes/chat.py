from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status

from app.api.dependencies import CurrentUser, get_rag_pipeline_service, get_conversation_repo
from app.application.services.rag_pipeline_service import RAGPipelineService
from app.infrastructure.repositories.sqlite_conversation_repo import SQLiteConversationRepository
from app.api.schemas.requests import ChatRequest
from app.api.schemas.responses import (
    ChatResponse,
    CitationResponse,
    EvidenceNodeResponse,
    EvidenceGraphResponse,
)
from app.domain.entities.rag import RAGRequest
from app.domain.entities.conversation import (
    Conversation,
    Message as DomMessage,
    MessageRole,
    Citation as DomCitation,
    ConversationScope,
)
from app.core.config import get_settings
from app.api.limiter import limiter

router = APIRouter(prefix="/chat", tags=["Chat"])
settings = get_settings()

@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a message",
    description="Submits a user query to the RAG pipeline to generate a citation-aware grounded response.",
)
@limiter.limit(settings.rate_limit_chat)
async def send_message(
    chat_request: ChatRequest,
    request: Request,
    current_user: CurrentUser,
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    user_id = current_user.id

    # 1. Retrieve or create conversation in SQL DB
    if chat_request.conversation_id:
        conversation = await conversation_repo.get_by_id(chat_request.conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found or access denied."
            )
    else:
        # Create a new conversation session
        doc_ids = (chat_request.retrieval_options or {}).get("document_ids", [])
        scope = ConversationScope.MULTI_DOCUMENT if len(doc_ids) > 1 else ConversationScope.DOCUMENT
        conversation = Conversation(
            user_id=user_id,
            scope=scope,
            document_ids=doc_ids,
        )
        conversation = await conversation_repo.create(conversation)

    # 2. Save user message to DB
    user_msg = DomMessage(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=chat_request.query,
    )
    await conversation_repo.add_message(user_msg)

    # 3. Compile context window from DB (excluding new message)
    history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in conversation.messages
        if msg.id != user_msg.id
    ][-10:]

    # Convert ChatRequest to RAGRequest domain model
    rag_request = RAGRequest(
        query=chat_request.query,
        workspace_id=chat_request.workspace_id,
        conversation_history=history,
        retrieval_options=chat_request.retrieval_options,
        generation_options=chat_request.generation_options,
    )

    # Call the application RAG pipeline service
    result = await pipeline_service.answer_question(rag_request)

    # Resolve supporting chunks text snippets
    chunk_snippets = {}
    if result.retrieval_result and result.retrieval_result.retrieved_chunks:
        chunk_snippets = {c.id: c.content for c in result.retrieval_result.retrieved_chunks}

    citations = [
        CitationResponse(
            citation_id=c.citation_id,
            document_id=c.document_id,
            document_title=c.document_title,
            pages=c.pages,
            supporting_chunks=[chunk_snippets.get(cid, cid) for cid in c.supporting_chunks],
            confidence=c.confidence,
            formatted_reference=c.formatted_reference,
        )
        for c in result.citations
    ]

    nodes = [
        EvidenceNodeResponse(
            statement=node.statement,
            supporting_chunks=node.supporting_chunks,
            confidence=node.confidence,
        )
        for node in result.evidence_graph.nodes
    ] if result.evidence_graph else []

    # 4. Map citations to domain entities
    dom_citations = [
        DomCitation(
            id=c.citation_id,
            document_id=c.document_id,
            document_title=c.document_title,
            page_number=c.pages[0] if c.pages else 1,
            section=c.formatted_reference,
            chunk_text=c.supporting_chunks[0] if c.supporting_chunks else "",
            relevance_score=c.confidence,
        )
        for c in result.citations
    ]

    # 5. Save assistant reply message to DB
    assistant_msg = DomMessage(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result.answer,
        citations=dom_citations,
    )
    await conversation_repo.add_message(assistant_msg)

    # 6. Update conversation modified timestamp
    await conversation_repo.update(conversation)

    return ChatResponse(
        answer=result.answer,
        conversation_id=conversation.id,
        citations=citations,
        confidence=result.confidence,
        evidence_graph=EvidenceGraphResponse(nodes=nodes),
        warnings=result.warnings,
    )

@router.get("/conversations")
async def list_conversations(
    current_user: CurrentUser,
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """Retrieve all conversations logged for the current user."""
    conversations = await conversation_repo.get_all(current_user.id)
    return [
        {
            "id": c.id,
            "title": c.title,
            "scope": c.scope,
            "document_ids": c.document_ids,
            "collection_id": c.collection_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in conversations
    ]

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """Retrieve full message history for a specific conversation session."""
    conversation = await conversation_repo.get_by_id(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found or access denied."
        )

    return [
        {
            "id": m.id,
            "role": m.role.value,
            "content": m.content,
            "citations": [
                {
                    "citation_id": c.id,
                    "document_id": c.document_id,
                    "document_title": c.document_title,
                    "pages": [c.page_number] if c.page_number else [],
                    "supporting_chunks": [c.chunk_text] if c.chunk_text else [],
                    "confidence": c.relevance_score,
                    "formatted_reference": c.section,
                }
                for c in m.citations
            ] if m.citations else [],
            "created_at": m.created_at,
        }
        for m in conversation.messages
    ]

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    conversation_repo: SQLiteConversationRepository = Depends(get_conversation_repo),
):
    """Delete a specific conversation session and all its messages."""
    success = await conversation_repo.delete(conversation_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found or access denied."
        )
    return {"status": "success"}
