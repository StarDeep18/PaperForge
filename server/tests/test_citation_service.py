"""
Unit Tests for the Citation Engine.

Tests the EvidenceMapper, CitationBuilder, ConfidenceScorer,
and CitationService orchestration, including the custom EvidenceGraph structure.
"""

import pytest
from app.domain.entities.chunk import Chunk
from app.domain.entities.retrieval import RetrievalResult, RetrievalInspector
from app.domain.entities.citation import (
    EvidenceReference,
    Citation,
    EvidenceNode,
    EvidenceGraph,
    CitationResult,
)
from app.domain.exceptions import EmptyEvidence, CitationError
from app.domain.services.evidence_mapper import EvidenceMapper
from app.domain.services.citation_builder import CitationBuilder
from app.domain.services.confidence_scorer import ConfidenceScorer
from app.domain.services.citation_service import CitationService


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    """Fixture returning test chunks from vector search matching double documents."""
    return [
        Chunk(
            id="chunk-1",
            document_id="doc-A.pdf",
            content="Quantum entanglement is a physical phenomenon where pairs or groups of particles generate shared states.",
            parent_content="Intro to Quantum: Quantum entanglement is a physical phenomenon where pairs or groups of particles generate shared states.",
            page_number=3,
            section_header="Quantum Physics",
            metadata={"title": "Introduction to Quantum"},
        ),
        Chunk(
            id="chunk-2",
            document_id="doc-A.pdf",
            content="Superposition allows a quantum system to be in multiple states simultaneously.",
            parent_content="Superposition allows a quantum system to be in multiple states simultaneously. This is key for computing.",
            page_number=4,
            section_header="Superposition",
            metadata={"title": "Introduction to Quantum", "similarity": 0.85},
        ),
        Chunk(
            id="chunk-3",
            document_id="doc-B.pdf",
            content="Qubits form the basic unit of quantum information, analogous to classical bits.",
            parent_content="Architecture: Qubits form the basic unit of quantum information, analogous to classical bits.",
            page_number=10,
            section_header="Hardware Architecture",
            metadata={"title": "Quantum Hardware Devices", "similarity": 0.65},
        ),
        Chunk(
            id="chunk-4",
            document_id="doc-A.pdf",
            content="Entangled systems can display correlations not explainable by classical physics.",
            parent_content="More Quantum: Entangled systems can display correlations not explainable by classical physics.",
            page_number=5,
            section_header="Quantum Physics",
            metadata={"title": "Introduction to Quantum", "similarity": 0.90},
        ),
    ]


@pytest.fixture
def sample_retrieval_result(sample_chunks) -> RetrievalResult:
    """Fixture returning RetrievalResult with mock inspector similarity list."""
    inspector = RetrievalInspector(
        query="quantum state theory",
        retrieved_chunk_ids=["chunk-1", "chunk-2", "chunk-3", "chunk-4"],
        similarity_scores=[0.95, 0.85, 0.65, 0.90],
    )
    return RetrievalResult(
        query="quantum state theory",
        retrieved_chunks=sample_chunks,
        total_chunks=4,
        inspector=inspector,
    )


# ── 1. Evidence Mapper Tests ─────────────────────────────────────────


def test_evidence_mapper_preserves_ordering_and_metadata(sample_retrieval_result):
    """Test that EvidenceMapper maps all chunks to references with ordering and scores intact."""
    mapper = EvidenceMapper()
    references = mapper.map_retrieval_result(sample_retrieval_result)
    
    assert len(references) == 4
    # Preserve ordering
    assert references[0].chunk_id == "chunk-1"
    assert references[1].chunk_id == "chunk-2"
    assert references[2].chunk_id == "chunk-3"
    assert references[3].chunk_id == "chunk-4"

    # Verify score preservation
    assert references[0].similarity_score == 0.95
    assert references[1].similarity_score == 0.85
    assert references[2].similarity_score == 0.65
    assert references[3].similarity_score == 0.90

    # Verify metadata titles and section mappings
    assert references[0].document_title == "Introduction to Quantum"
    assert references[0].page_number == 3
    assert references[0].section_heading == "Quantum Physics"
    
    assert references[2].document_title == "Quantum Hardware Devices"
    assert references[2].page_number == 10
    assert references[2].section_heading == "Hardware Architecture"


def test_evidence_mapper_snippet_truncation(sample_retrieval_result):
    """Test that generated snippet lengths do not exceed strict custom limits."""
    mapper = EvidenceMapper()
    references = mapper.map_retrieval_result(sample_retrieval_result, max_snippet_length=15)
    
    # Verify strict truncation + ellipses
    assert len(references[0].snippet) <= 18  # 15 + "..." length
    assert references[0].snippet.endswith("...")


# ── 2. Citation Builder Tests ────────────────────────────────────────


def test_citation_builder_page_merging():
    """Verify merging ranges for consecutive list elements."""
    builder = CitationBuilder()
    
    # Consecutive ranges
    assert builder.merge_pages([1, 2, 3, 5], policy="consecutive") == "1-3, 5"
    assert builder.merge_pages([10, 11, 12, 14, 15], policy="consecutive") == "10-12, 14-15"
    
    # Non-consecutive policy
    assert builder.merge_pages([1, 2, 3, 5], policy="none") == "1, 2, 3, 5"
    
    # Empty page scenarios
    assert builder.merge_pages([]) == ""
    assert builder.merge_pages([None]) == ""


def test_citation_builder_groups_by_document(sample_retrieval_result):
    """Test grouping and consolidating duplicate page lists for single and multiple papers."""
    mapper = EvidenceMapper()
    builder = CitationBuilder()
    
    references = mapper.map_retrieval_result(sample_retrieval_result)
    citations = builder.build_citations(references)
    
    # 4 references mapped to 2 documents: doc-A.pdf and doc-B.pdf
    assert len(citations) == 2
    
    cit_A = next(c for c in citations if c.document_id == "doc-A.pdf")
    assert cit_A.document_title == "Introduction to Quantum"
    assert set(cit_A.pages) == {3, 4, 5}
    assert cit_A.formatted_reference == "Introduction to Quantum, p. 3-5"
    
    cit_B = next(c for c in citations if c.document_id == "doc-B.pdf")
    assert cit_B.document_title == "Quantum Hardware Devices"
    assert cit_B.pages == [10]
    assert cit_B.formatted_reference == "Quantum Hardware Devices, p. 10"


# ── 3. Confidence Scorer Tests ───────────────────────────────────────


def test_confidence_scorer_thresholds(sample_retrieval_result):
    """Verify confidence category mapping matches configured threshold parameters."""
    mapper = EvidenceMapper()
    scorer = ConfidenceScorer()
    
    references = mapper.map_retrieval_result(sample_retrieval_result)
    
    # High confidence test
    cat, score = scorer.score_evidence(references, high_threshold=0.6, medium_threshold=0.4)
    assert cat == "High"
    assert score > 0.6
    
    # Low confidence test
    # Set high similarity scores close to zero to force low confidence
    for r in references:
        r.similarity_score = 0.15
        
    cat, score = scorer.score_evidence(references, high_threshold=0.7, medium_threshold=0.4)
    assert cat == "Low"
    assert score < 0.4


# ── 4. Citation Service Orchestration & Evidence Graph Tests ──────────


def test_citation_service_empty_evidence_raises():
    """Verify that EmptyEvidence exception is thrown when retrieval result contains no context chunks."""
    service = CitationService()
    
    empty_result = RetrievalResult(
        query="query",
        retrieved_chunks=[],
        total_chunks=0,
    )
    
    with pytest.raises(EmptyEvidence):
        service.generate_citations("The answer text", empty_result)
        
    with pytest.raises(EmptyEvidence):
        service.generate_citations("The answer text", None)


def test_citation_service_orchestration_success(sample_retrieval_result):
    """Verify successful end-to-end integration, formatting, confidence scoring, and mapping."""
    service = CitationService()
    
    answer_text = (
        "Quantum entanglement binds particles together [1]. "
        "Also, superposition states enable multiple parallel paths [2]. "
        "Qubits are classical analogues [3]."
    )
    
    result = service.generate_citations(answer_text, sample_retrieval_result)
    
    assert isinstance(result, CitationResult)
    assert result.answer == answer_text
    assert len(result.citations) == 2  # doc-A.pdf and doc-B.pdf
    assert len(result.evidence) == 4
    assert result.overall_confidence in ("High", "Medium", "Low")
    
    # Verify warnings filter out references below min confidence threshold
    # Default config min confidence threshold is 0.3, so all chunks are kept.
    assert len(result.warnings) == 0


def test_evidence_graph_sentence_bracket_mapping(sample_retrieval_result):
    """Verify that the internal EvidenceGraph maps bracket indices (e.g. [1]) correctly."""
    service = CitationService()
    
    answer_text = (
        "Statement 1 matches the first chunk [1].\n"
        "Statement 2 matches the second and fourth chunk [2] [4].\n"
        "Statement 3 has no citations."
    )
    
    result = service.generate_citations(answer_text, sample_retrieval_result)
    graph = result.evidence_graph
    
    assert isinstance(graph, EvidenceGraph)
    assert len(graph.nodes) == 3
    
    # Node 1 matches index [1] -> chunk-1
    assert graph.nodes[0].statement == "Statement 1 matches the first chunk [1]."
    assert graph.nodes[0].supporting_chunks == ["chunk-1"]
    
    # Node 2 matches index [2] [4] -> chunk-2 and chunk-4
    assert graph.nodes[1].statement == "Statement 2 matches the second and fourth chunk [2] [4]."
    assert set(graph.nodes[1].supporting_chunks) == {"chunk-2", "chunk-4"}
    
    # Node 3 has no bracket citations, so it defaults to matching empty or text-overlap
    assert graph.nodes[2].statement == "Statement 3 has no citations."


def test_evidence_graph_word_overlap_fallback_mapping(sample_retrieval_result):
    """Test text overlap matching when bracket references are omitted."""
    service = CitationService()
    
    # statement 1 shares keywords "superposition allowing quantum system multiple states" with chunk-2
    # statement 2 shares keywords "qubits classical bits analog basic unit" with chunk-3
    answer_text = (
        "Superposition is a state allowing a quantum system to explore multiple states.\n"
        "This is how qubits function as basic units of classical analog information."
    )
    
    result = service.generate_citations(answer_text, sample_retrieval_result)
    graph = result.evidence_graph
    
    assert len(graph.nodes) == 2
    # Node 1 matches chunk-2
    assert "chunk-2" in graph.nodes[0].supporting_chunks
    # Node 2 matches chunk-3
    assert "chunk-3" in graph.nodes[1].supporting_chunks
