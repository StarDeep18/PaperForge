"""
API Documents Router.
"""

import os
import asyncio
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Request, Query
from fastapi.responses import FileResponse
from typing import Optional, List

from app.api.dependencies import CurrentUserId, get_rag_pipeline_service
from app.application.services.rag_pipeline_service import RAGPipelineService
from app.api.schemas.responses import DocumentResponse, UploadResponse, DocumentMetadataResponse, PaginatedDocumentResponse
from app.domain.entities.document import Document
from app.api.limiter import limiter

router = APIRouter(prefix="/documents", tags=["Documents"])


def _map_document_to_response(doc: Document) -> DocumentResponse:
    meta = doc.metadata
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        file_type=doc.file_type.value,
        status=doc.status.value,
        metadata=DocumentMetadataResponse(
            title=meta.title if meta else None,
            authors=meta.authors if meta and meta.authors else [],
            abstract=meta.abstract if meta else None,
            publication_date=meta.publication_date if meta else None,
            journal=meta.journal if meta else None,
            doi=meta.doi if meta else None,
            keywords=meta.keywords if meta and meta.keywords else [],
            page_count=meta.page_count if meta else 0,
            word_count=meta.word_count if meta else 0,
        ),
        collection_id=doc.collection_id,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post(
    "/upload",
    response_model=List[UploadResponse],
    status_code=201,
    summary="Upload and process documents",
    description="Synchronously uploads, parses, chunks, embeds, and stores one or more research papers (PDF, DOCX, TXT) in the vector database.",
)
@limiter.limit("20/minute")
async def upload_documents(
    user_id: CurrentUserId,
    request: Request,
    files: List[UploadFile] = File(..., description="The files to upload and process."),
    collection_id: Optional[str] = Form(None, description="Optional collection ID scoping."),
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    responses = []
    for file in files:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"Uploaded file '{file.filename}' is empty.")

        # Ingest document synchronously
        result = await pipeline_service.ingest_document(
            filename=file.filename or "unknown",
            content=content,
            user_id=user_id,
            collection_id=collection_id,
        )

        responses.append(
            UploadResponse(
                document_id=result.document_id,
                filename=file.filename or "unknown",
                pages=result.pages,
                chunks=result.chunks,
                processing_time=result.duration,
                warnings=result.warnings,
            )
        )
    return responses


@router.get(
    "",
    response_model=PaginatedDocumentResponse,
    summary="List uploaded documents",
    description="Returns a paginated list of all documents uploaded by the current user.",
)
async def list_documents(
    user_id: CurrentUserId,
    collection_id: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    limit = size
    offset = (page - 1) * size

    # Retrieve documents and count in parallel using asyncio.gather
    documents_task = pipeline_service.list_documents(
        user_id=user_id,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )
    count_task = pipeline_service.count_documents(
        user_id=user_id,
        collection_id=collection_id,
    )

    documents, total = await asyncio.gather(documents_task, count_task)
    pages = (total + size - 1) // size
    items = [_map_document_to_response(doc) for doc in documents]

    return PaginatedDocumentResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieves metadata details and status of a single document by ID.",
)
async def get_document(
    document_id: str,
    user_id: CurrentUserId,
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    doc = await pipeline_service.get_document(document_id, user_id)
    return _map_document_to_response(doc)


@router.get(
    "/{document_id}/file",
    summary="Get document raw file",
    description="Serves the physical document file (e.g. PDF) directly from disk.",
)
async def get_document_file(
    document_id: str,
    user_id: CurrentUserId,
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    doc = await pipeline_service.get_document(document_id, user_id)
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Physical file not found.")
    
    media_type = "application/pdf" if doc.file_type.value.lower() == "pdf" else "application/octet-stream"
    return FileResponse(doc.file_path, media_type=media_type, filename=doc.original_filename)


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete a document",
    description="Deletes a document record, physical file, and all associated embeddings/vectors.",
)
async def delete_document(
    document_id: str,
    user_id: CurrentUserId,
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    await pipeline_service.delete_document(document_id, user_id)
    return None

