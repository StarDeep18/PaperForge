from fastapi import APIRouter, Depends, Request

from app.api.dependencies import CurrentUserId, get_rag_pipeline_service
from app.application.services.rag_pipeline_service import RAGPipelineService
from app.api.schemas.requests import ChatRequest
from app.api.schemas.responses import (
    ChatResponse,
    CitationResponse,
    EvidenceNodeResponse,
    EvidenceGraphResponse,
)
from app.domain.entities.rag import RAGRequest
from app.api.limiter import limiter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a message",
    description="Submits a user query to the RAG pipeline to generate a citation-aware grounded response.",
)
@limiter.limit("5/minute")
async def send_message(
    chat_request: ChatRequest,
    request: Request,
    user_id: CurrentUserId,
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    # Convert ChatRequest to RAGRequest domain model
    rag_request = RAGRequest(
        query=chat_request.query,
        workspace_id=chat_request.workspace_id,
        conversation_history=chat_request.conversation_history,
        retrieval_options=chat_request.retrieval_options,
        generation_options=chat_request.generation_options,
    )

    # Call the application pipeline service
    result = await pipeline_service.answer_question(rag_request)

    # Serialize domain objects into responses Pydantic schemas
    citations = [
        CitationResponse(
            citation_id=c.citation_id,
            document_id=c.document_id,
            document_title=c.document_title,
            pages=c.pages,
            supporting_chunks=c.supporting_chunks,
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

    return ChatResponse(
        answer=result.answer,
        citations=citations,
        confidence=result.confidence,
        evidence_graph=EvidenceGraphResponse(nodes=nodes),
        warnings=result.warnings,
    )
