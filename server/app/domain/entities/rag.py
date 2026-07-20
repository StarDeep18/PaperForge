"""
RAG Pipeline Domain Models.

Standardized models for document processing results, query requests, and end-to-end QA responses.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from app.domain.entities.citation import Citation, EvidenceGraph
from app.domain.entities.retrieval import RetrievalResult
from app.domain.entities.generation import GenerationMetrics, PromptInspector


@dataclass
class DocumentProcessingResult:
    """
    Unified summary of a processed document ingestion workflow.
    """
    success: bool
    document_id: str
    pages: int
    chunks: int
    embeddings: int
    duration: float  # processing time in seconds
    warnings: list[str] = field(default_factory=list)


@dataclass
class RAGRequest:
    """
    Unified entrypoint request payload for end-to-end question answering.
    """
    query: str
    workspace_id: Optional[str] = None
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    retrieval_options: dict[str, Any] = field(default_factory=dict)
    generation_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResponse:
    """
    Unified final grounding response returned by the QA RAG pipeline service.
    """
    answer: str
    citations: list[Citation]
    confidence: str
    evidence_graph: EvidenceGraph
    retrieval_result: RetrievalResult
    generation_metrics: GenerationMetrics
    prompt_inspector: PromptInspector
    warnings: list[str] = field(default_factory=list)
