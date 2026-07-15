"""
Citation Domain Entities.

Provides structured models for referencing source evidence, documenting confidence,
grouping references into citations, and building internal statement-evidence graphs.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvidenceReference:
    """
    Direct granular mapping of a document chunk used as RAG evidence.
    """

    chunk_id: str
    parent_chunk_id: Optional[str]
    document_id: str
    document_title: str
    page_number: Optional[int]
    section_heading: Optional[str]
    similarity_score: float
    confidence: float  # Normalized numeric score
    snippet: str


@dataclass
class Citation:
    """
    High-level citation metadata grouping evidence references.
    """

    citation_id: str
    document_id: str
    document_title: str
    pages: list[int] = field(default_factory=list)
    supporting_chunks: list[str] = field(default_factory=list)  # list of chunk_ids
    confidence: str = "Medium"  # "High", "Medium", or "Low"
    formatted_reference: str = ""


@dataclass
class EvidenceNode:
    """
    Represents an individual statement from the generated answer
    and lists its direct supporting evidence.
    """

    statement: str
    supporting_chunks: list[str] = field(default_factory=list)  # list of chunk_ids
    confidence: float = 0.0  # Combined confidence score for the statement


@dataclass
class EvidenceGraph:
    """
    Internal model linking generated statements to supporting document chunks.
    Allows features like interactive highlighted references and side-by-side verification.
    """

    nodes: list[EvidenceNode] = field(default_factory=list)


@dataclass
class CitationResult:
    """
    Structured citation result wrapping answer, citations, evidence list,
    and diagnostic metrics.
    """

    answer: str
    citations: list[Citation] = field(default_factory=list)
    evidence: list[EvidenceReference] = field(default_factory=list)
    overall_confidence: str = "Medium"  # "High", "Medium", or "Low"
    warnings: list[str] = field(default_factory=list)
    evidence_graph: Optional[EvidenceGraph] = None
