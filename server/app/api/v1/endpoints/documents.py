"""
Documents API Endpoints.

Handles document upload, listing, retrieval, and deletion.
"""

import asyncio
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api.dependencies import (
    CurrentUserId,
    get_document_repo,
    get_upload_document_use_case,
    get_process_document_use_case,
    get_vector_store,
    get_file_storage,
)
from app.api.v1.schemas.documents import (
    DocumentListResponse,
    DocumentMetadataResponse,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentUpdateRequest,
)
from app.application.documents.upload_document import UploadDocumentUseCase
from app.application.documents.process_document import ProcessDocumentUseCase
from app.domain.entities.document import Document
from app.domain.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.infrastructure.repositories.sqlite_document_repo import SQLiteDocumentRepository
from app.infrastructure.repositories.chroma_vector_store import ChromaVectorStore
from app.infrastructure.storage.local_file_storage import LocalFileStorage

router = APIRouter(prefix="/documents", tags=["Documents"])


def _document_to_response(doc: Document) -> DocumentResponse:
    """Map domain entity to API response."""
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        file_type=doc.file_type.value,
        status=doc.status.value,
        metadata=DocumentMetadataResponse(
            title=doc.metadata.title if doc.metadata else None,
            authors=doc.metadata.authors if doc.metadata else [],
            abstract=doc.metadata.abstract if doc.metadata else None,
            publication_date=doc.metadata.publication_date if doc.metadata else None,
            journal=doc.metadata.journal if doc.metadata else None,
            doi=doc.metadata.doi if doc.metadata else None,
            keywords=doc.metadata.keywords if doc.metadata else [],
            page_count=doc.metadata.page_count if doc.metadata else 0,
            word_count=doc.metadata.word_count if doc.metadata else 0,
        ),
        collection_id=doc.collection_id,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection_id: Optional[str] = Form(None),
    user_id: str = Depends(CurrentUserId),
    upload_use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    process_use_case: ProcessDocumentUseCase = Depends(get_process_document_use_case),
):
    """
    Upload a research paper (PDF, DOCX, or TXT).

    The document is saved immediately and processing (parse → chunk → embed)
    runs in the background. Poll the document status endpoint to track progress.
    """
    try:
        content = await file.read()
        document = await upload_use_case.execute(
            filename=file.filename or "unknown",
            content=content,
            user_id=user_id,
            collection_id=collection_id,
        )

        # Process in background
        background_tasks.add_task(process_use_case.execute, document)

        return DocumentUploadResponse(
            id=document.id,
            filename=document.original_filename,
            status=document.status.value,
        )

    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    user_id: str = Depends(CurrentUserId),
    collection_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    document_repo: SQLiteDocumentRepository = Depends(get_document_repo),
):
    """List all documents for the current user, optionally filtered by collection."""
    documents = await document_repo.get_all(
        user_id=user_id,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )
    total = await document_repo.count(user_id=user_id, collection_id=collection_id)

    return DocumentListResponse(
        documents=[_document_to_response(d) for d in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: str,
    user_id: str = Depends(CurrentUserId),
    document_repo: SQLiteDocumentRepository = Depends(get_document_repo),
):
    """Retrieve a single document by ID."""
    document = await document_repo.get_by_id(document_id, user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_to_response(document)


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    user_id: str = Depends(CurrentUserId),
    document_repo: SQLiteDocumentRepository = Depends(get_document_repo),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
    file_storage: LocalFileStorage = Depends(get_file_storage),
):
    """Delete a document and all associated data (chunks, embeddings, file)."""
    document = await document_repo.get_by_id(document_id, user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    await vector_store.delete_by_document(document_id)

    # Delete file from disk
    await file_storage.delete_file(document.file_path)

    # Delete from database
    await document_repo.delete(document_id, user_id)

    return None
