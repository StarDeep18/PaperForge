"""
API Response Models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


class UploadResponse(BaseModel):
    """
    Ingestion details returned after a document has been successfully processed.
    """
    document_id: str = Field(..., description="Unique UUID assigned to the document.")
    filename: str = Field(..., description="Name of the processed file.")
    pages: int = Field(..., description="Total pages extracted from the document.")
    chunks: int = Field(..., description="Total chunks generated during chunking.")
    processing_time: float = Field(..., description="Duration of the ingestion process in seconds.")
    warnings: List[str] = Field(default_factory=list, description="Any warnings logged during processing.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc-a1b2c3d4",
                "filename": "quantum_mechanics.pdf",
                "pages": 14,
                "chunks": 42,
                "processing_time": 3.84,
                "warnings": []
            }
        }
    }


class CitationResponse(BaseModel):
    """
    Detailed citation grounding references.
    """
    citation_id: str
    document_id: str
    document_title: str
    pages: List[int] = Field(default_factory=list)
    supporting_chunks: List[str] = Field(default_factory=list)
    confidence: str = "Medium"
    formatted_reference: str = ""


class EvidenceNodeResponse(BaseModel):
    """
    Single statement and supporting references in the EvidenceGraph.
    """
    statement: str
    supporting_chunks: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class EvidenceGraphResponse(BaseModel):
    """
    Statement-evidence graph showing how assertions trace back to document chunks.
    """
    nodes: List[EvidenceNodeResponse] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """
    Grounding response returned after answering a query.
    """
    answer: str = Field(..., description="Synthesized answer text.")
    conversation_id: Optional[str] = Field(None, description="The SQL database UUID string of the conversation.")
    citations: List[CitationResponse] = Field(default_factory=list, description="Grounding source citations.")
    confidence: str = Field(..., description="Overall confidence level (High, Medium, Low).")
    evidence_graph: EvidenceGraphResponse = Field(..., description="Statement-chunk evidence relationships graph.")
    warnings: List[str] = Field(default_factory=list, description="Any execution warnings.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "Quantum superposition is a fundamental principle where a physical system exists in multiple states simultaneously. [1]",
                "citations": [
                    {
                        "citation_id": "1",
                        "document_id": "doc-a1b2c3d4",
                        "document_title": "quantum_mechanics.pdf",
                        "pages": [3],
                        "supporting_chunks": ["Superposition allows simultaneous states..."],
                        "confidence": "High",
                        "formatted_reference": "[1] quantum_mechanics.pdf, Page 3"
                    }
                ],
                "confidence": "High",
                "evidence_graph": {
                    "nodes": [
                        {
                            "statement": "Quantum superposition allows multiple concurrent states.",
                            "supporting_chunks": ["Superposition allows simultaneous states..."],
                            "confidence": 0.95
                        }
                    ]
                },
                "warnings": []
            }
        }
    }


class DocumentMetadataResponse(BaseModel):
    """
    Extracted document metadata details.
    """
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    page_count: int = 0
    word_count: int = 0


class DocumentResponse(BaseModel):
    """
    Full document record payload.
    """
    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: str
    metadata: DocumentMetadataResponse
    collection_id: Optional[str] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "doc-a1b2c3d4",
                "filename": "stored_quantum_mechanics.pdf",
                "original_filename": "quantum_mechanics.pdf",
                "file_size": 245000,
                "file_type": "pdf",
                "status": "ready",
                "metadata": {
                    "title": "Introduction to Quantum Mechanics",
                    "authors": ["Richard Feynman"],
                    "abstract": "An overview of superposition.",
                    "publication_date": "1965",
                    "journal": "Caltech Press",
                    "doi": "10.1016/j.jmr.2024.10",
                    "keywords": ["quantum", "physics"],
                    "page_count": 14,
                    "word_count": 4500
                },
                "collection_id": "collection-999",
                "chunk_count": 42,
                "error_message": None,
                "created_at": "2026-07-20T12:00:00Z",
                "updated_at": "2026-07-20T12:01:00Z"
            }
        }
    }


class PaginatedDocumentResponse(BaseModel):
    """
    Structured pagination metadata and items payload.
    """
    items: List[DocumentResponse] = Field(..., description="List of documents on the current page.")
    total: int = Field(..., description="Total documents matching the query filter.")
    page: int = Field(..., description="Current page number.")
    size: int = Field(..., description="Number of items per page.")
    pages: int = Field(..., description="Total pages available.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "doc-a1b2c3d4",
                        "filename": "stored_quantum_mechanics.pdf",
                        "original_filename": "quantum_mechanics.pdf",
                        "file_size": 245000,
                        "file_type": "pdf",
                        "status": "ready",
                        "metadata": {
                            "title": "Introduction to Quantum Mechanics",
                            "authors": ["Richard Feynman"],
                            "page_count": 14,
                            "word_count": 4500
                        },
                        "collection_id": None,
                        "chunk_count": 42,
                        "created_at": "2026-07-20T12:00:00Z",
                        "updated_at": "2026-07-20T12:01:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1
            }
        }
    }


class HealthResponse(BaseModel):
    """
    Health check status details of all system components.
    """
    upload_service: str
    parser: str
    embedding_provider: str
    vector_store: str
    retrieval: str
    generation: str
    citation: str
    overall_status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_service": "healthy",
                "parser": "healthy",
                "embedding_provider": "healthy",
                "vector_store": "healthy",
                "retrieval": "healthy",
                "generation": "healthy",
                "citation": "healthy",
                "overall_status": "healthy"
            }
        }
    }


class ErrorResponse(BaseModel):
    """
    Consistent JSON error payload.
    """
    error: str = Field(..., description="Machine-readable error type/class.")
    message: str = Field(..., description="Human-friendly explanation.")
    details: Optional[Any] = Field(None, description="Detailed contextual data (if available).")

