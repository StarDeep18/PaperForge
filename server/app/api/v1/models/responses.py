"""
API v1 Response Models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
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
    citations: List[CitationResponse] = Field(default_factory=list, description="Grounding source citations.")
    confidence: str = Field(..., description="Overall confidence level (High, Medium, Low).")
    evidence_graph: EvidenceGraphResponse = Field(..., description="Statement-chunk evidence relationships graph.")
    warnings: List[str] = Field(default_factory=list, description="Any execution warnings.")


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


class ErrorResponse(BaseModel):
    """
    Consistent JSON error payload.
    """
    error: str = Field(..., description="Machine-readable error type/class.")
    message: str = Field(..., description="Human-friendly explanation.")
    details: Optional[Any] = Field(None, description="Detailed contextual data (if available).")
