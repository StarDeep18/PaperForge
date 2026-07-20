"""
Integration Tests for RAGPipelineService.
"""

import pytest
import time
from typing import Any, Optional
from unittest.mock import MagicMock, AsyncMock

from app.domain.entities.document import Document, DocumentStatus, DocumentType, DocumentMetadata
from app.domain.entities.rag import RAGRequest, RAGResponse, DocumentProcessingResult
from app.domain.entities.chunk import Chunk
from app.domain.entities.retrieval import RetrievalResult, ContextWindow
from app.domain.entities.generation import GenerationMetrics, PromptInspector
from app.domain.entities.citation import Citation, EvidenceGraph, EvidenceNode, CitationResult
from app.application.services.rag_pipeline_service import RAGPipelineService
from app.domain.exceptions import (
    PipelineInitializationFailure,
    DocumentProcessingFailure,
    QuestionAnsweringFailure,
    ProviderHealthFailure,
    RetrievalError,
    GenerationError,
    PaperForgeError,
)
from app.infrastructure.ai.mock_llm_provider import MockLLMProvider
from app.infrastructure.ai.mock_embedding_provider import MockEmbeddingProvider
from tests.test_vector_store_service import MockVectorStore


# ── Mocks and Fakes ──────────────────────────────────────────────────

class MockDocumentRepository:
    """Fake in-memory document repository."""
    def __init__(self):
        self.documents = {}

    async def create(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def update(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def get_by_id(self, document_id: str, user_id: Optional[str] = None) -> Optional[Document]:
        return self.documents.get(document_id)


class MockFileStorage:
    """Fake in-memory local file storage."""
    def __init__(self, exists_flag: bool = True):
        self._exists_flag = exists_flag
        self._upload_dir = MagicMock()
        self._upload_dir.exists.return_value = exists_flag

    async def save_file(self, content: bytes, original_filename: str, user_id: str) -> tuple[str, str]:
        return "stored_name.pdf", "/fake/path/stored_name.pdf"

    async def delete_file(self, file_path: str) -> bool:
        return True


class MockParser:
    """Fake parser returning static text parsing results."""
    def __init__(self, text: str = "Mock paper content.", page_count: int = 1):
        self.text = text
        self.page_count = page_count

    def parse(self, file_path: str, file_type: Any) -> Any:
        res = MagicMock()
        res.text = self.text
        res.metadata = DocumentMetadata(page_count=self.page_count, word_count=len(self.text.split()))
        res.page_breaks = {}
        return res


# ── Test Suite ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initialization_failure():
    """Verify that initialization fails if dependencies are missing."""
    with pytest.raises(PipelineInitializationFailure):
        RAGPipelineService(
            document_repo=None,
            upload_use_case=None,
            process_document_use_case=None,
            retrieval_service=None,
            generation_service=None,
            citation_service=None,
            file_storage=None,
            parser_factory=None,
            vector_store_service=None,
        )


@pytest.mark.asyncio
async def test_document_processing_success():
    """Verify that process_document successfully completes parser -> chunk -> embed -> store."""
    doc_repo = MockDocumentRepository()
    upload_use_case = MagicMock()
    
    # Setup real ProcessDocumentUseCase with fake/mock dependencies
    from app.application.documents.process_document import ProcessDocumentUseCase
    from app.domain.services.vector_store_service import VectorStoreService
    from app.domain.services.embedding_service import EmbeddingService
    
    vector_store = MockVectorStore()
    vs_service = VectorStoreService(vector_store)
    emb_provider = MockEmbeddingProvider()
    emb_service = EmbeddingService(emb_provider)
    
    parser_factory = MagicMock()
    mock_parser_result = MagicMock()
    mock_parser_result.text = "This is a scientific paper. Quantum mechanics is fun. [1]"
    mock_parser_result.metadata = DocumentMetadata(page_count=3, word_count=10)
    mock_parser_result.page_breaks = {0: 1, 25: 2}
    parser_factory.parse.return_value = mock_parser_result
    
    process_use_case = ProcessDocumentUseCase(
        document_repo=doc_repo,
        vector_store_service=vs_service,
        embedding_service=emb_service,
        parser_factory=parser_factory,
    )
    
    file_storage = MockFileStorage()
    retrieval_service = MagicMock()
    generation_service = MagicMock()
    citation_service = MagicMock()
    
    pipeline = RAGPipelineService(
        document_repo=doc_repo,
        upload_use_case=upload_use_case,
        process_document_use_case=process_use_case,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        citation_service=citation_service,
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=vs_service,
    )
    
    doc = Document(
        user_id="user-123",
        filename="stored.pdf",
        original_filename="paper.pdf",
        file_path="/fake/path.pdf",
        file_size=1000,
        file_type=DocumentType.PDF,
        status=DocumentStatus.UPLOADED,
    )
    await doc_repo.create(doc)
    
    result = await pipeline.process_document(doc)
    
    assert isinstance(result, DocumentProcessingResult)
    assert result.success is True
    assert result.document_id == doc.id
    assert result.pages == 3
    assert result.chunks > 0
    assert result.embeddings == result.chunks
    assert result.duration > 0.0
    assert len(result.warnings) == 0


@pytest.mark.asyncio
async def test_document_processing_failure():
    """Verify that a failure during document processing is translated to DocumentProcessingFailure."""
    doc_repo = MockDocumentRepository()
    upload_use_case = MagicMock()
    process_use_case = MagicMock()
    process_use_case.execute.side_effect = Exception("Simulated parsing crash")
    
    file_storage = MockFileStorage()
    retrieval_service = MagicMock()
    generation_service = MagicMock()
    citation_service = MagicMock()
    parser_factory = MagicMock()
    
    pipeline = RAGPipelineService(
        document_repo=doc_repo,
        upload_use_case=upload_use_case,
        process_document_use_case=process_use_case,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        citation_service=citation_service,
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=MagicMock(),
    )
    
    doc = Document(
        user_id="user-123",
        filename="stored.pdf",
        original_filename="paper.pdf",
        file_path="/fake/path.pdf",
        file_type=DocumentType.PDF,
    )
    
    with pytest.raises(DocumentProcessingFailure) as exc:
        await pipeline.process_document(doc)
    
    assert "Simulated parsing crash" in str(exc.value)


@pytest.mark.asyncio
async def test_answer_question_success():
    """Verify that question answering successfully chains retrieval -> generation -> citation."""
    doc_repo = MockDocumentRepository()
    upload_use_case = MagicMock()
    process_use_case = MagicMock()
    file_storage = MockFileStorage()
    parser_factory = MagicMock()
    
    # Setup mock retrieval
    ret_service = MagicMock()
    chunk = Chunk(id="chunk-1", document_id="doc-1", content="Quantum states can exist in superposition. [1]")
    ret_result = RetrievalResult(
        query="Explain quantum states",
        retrieved_chunks=[chunk],
        total_chunks=1,
        retrieval_duration=5.0,
        embedding_duration=2.0,
        search_duration=3.0,
        applied_filters={},
        warnings=[],
        context_window=ContextWindow(ordered_chunks=[chunk], estimated_tokens=10, remaining_budget=4000),
    )
    ret_service.retrieve = AsyncMock(return_value=ret_result)
    
    # Setup mock generation
    gen_service = MagicMock()
    gen_metrics = GenerationMetrics(duration=0.5, prompt_tokens_estimated=20, response_tokens_estimated=15)
    prompt_ins = PromptInspector(system_instruction="sys", user_prompt="user", estimated_tokens=20, context_size_chars=40, template_used="default")
    gen_result = MagicMock()
    gen_result.response = "Quantum states can exist in superposition. [1]"
    gen_result.provider = "gemini"
    gen_result.model = "gemini-pro"
    gen_result.metrics = gen_metrics
    gen_result.inspector = prompt_ins
    gen_result.warnings = []
    gen_service.generate = AsyncMock(return_value=gen_result)
    
    # Setup mock citation
    cit_service = MagicMock()
    citation = Citation(citation_id="1", document_id="doc-1", document_title="Quantum Physics", pages=[1], supporting_chunks=["chunk-1"], confidence="High", formatted_reference="[1] doc-1, Page 1")
    evidence_graph = EvidenceGraph(nodes=[EvidenceNode(statement="Quantum states can exist in superposition.", supporting_chunks=["chunk-1"], confidence=0.9)])
    cit_result = CitationResult(
        answer="Quantum states can exist in superposition. [1]",
        citations=[citation],
        evidence=[],
        overall_confidence="High",
        warnings=[],
        evidence_graph=evidence_graph,
    )
    cit_service.generate_citations.return_value = cit_result
    
    pipeline = RAGPipelineService(
        document_repo=doc_repo,
        upload_use_case=upload_use_case,
        process_document_use_case=process_use_case,
        retrieval_service=ret_service,
        generation_service=gen_service,
        citation_service=cit_service,
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=MagicMock(),
    )
    
    request = RAGRequest(
        query="Explain quantum states",
        workspace_id="ws-abc",
        conversation_history=[{"role": "user", "content": "hello"}],
        retrieval_options={"top_k": 5},
        generation_options={"temperature": 0.2},
    )
    
    response = await pipeline.answer_question(request)
    
    assert isinstance(response, RAGResponse)
    assert response.answer == "Quantum states can exist in superposition. [1]"
    assert len(response.citations) == 1
    assert response.citations[0].document_id == "doc-1"
    assert response.confidence == "High"
    assert response.evidence_graph == evidence_graph
    assert response.retrieval_result == ret_result
    assert response.generation_metrics == gen_metrics
    assert response.prompt_inspector == prompt_ins
    assert len(response.warnings) == 0


@pytest.mark.asyncio
async def test_answer_question_validation_failure():
    """Verify that an empty query raises QuestionAnsweringFailure."""
    pipeline = RAGPipelineService(
        document_repo=MagicMock(),
        upload_use_case=MagicMock(),
        process_document_use_case=MagicMock(),
        retrieval_service=MagicMock(),
        generation_service=MagicMock(),
        citation_service=MagicMock(),
        file_storage=MagicMock(),
        parser_factory=MagicMock(),
        vector_store_service=MagicMock(),
    )
    
    with pytest.raises(QuestionAnsweringFailure) as exc:
        await pipeline.answer_question(RAGRequest(query="   "))
    assert "Query text cannot be empty" in str(exc.value)


@pytest.mark.asyncio
async def test_answer_question_provider_failure():
    """Verify that exceptions in lower-level services are mapped to QuestionAnsweringFailure."""
    ret_service = MagicMock()
    ret_service.retrieve.side_effect = RetrievalError("Simulated retrieval connection error")
    
    pipeline = RAGPipelineService(
        document_repo=MagicMock(),
        upload_use_case=MagicMock(),
        process_document_use_case=MagicMock(),
        retrieval_service=ret_service,
        generation_service=MagicMock(),
        citation_service=MagicMock(),
        file_storage=MagicMock(),
        parser_factory=MagicMock(),
        vector_store_service=MagicMock(),
    )
    
    with pytest.raises(QuestionAnsweringFailure) as exc:
        await pipeline.answer_question(RAGRequest(query="Help"))
    assert "Simulated retrieval connection error" in str(exc.value)


@pytest.mark.asyncio
async def test_health_check_success():
    """Verify that a successful health check returns details of all components."""
    file_storage = MockFileStorage(exists_flag=True)
    parser_factory = MagicMock()
    parser_factory._pdf_parser = MagicMock()
    parser_factory._docx_parser = MagicMock()
    
    emb_provider = MagicMock()
    emb_provider.health_check = AsyncMock(return_value=True)
    
    vs_service = MagicMock()
    vs_service.health_check = AsyncMock(return_value={"status": "healthy"})
    
    ret_service = MagicMock()
    ret_service._embedding_provider = emb_provider
    ret_service._vector_store_service = vs_service
    
    llm_provider = MagicMock()
    llm_provider.health_check = AsyncMock(return_value=True)
    gen_service = MagicMock()
    gen_service.provider = llm_provider
    
    pipeline = RAGPipelineService(
        document_repo=MagicMock(),
        upload_use_case=MagicMock(),
        process_document_use_case=MagicMock(),
        retrieval_service=ret_service,
        generation_service=gen_service,
        citation_service=MagicMock(),
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=vs_service,
    )
    
    report = await pipeline.health_check()
    assert report["upload_service"] == "healthy"
    assert report["parser"] == "healthy"
    assert report["embedding_provider"] == "healthy"
    assert report["vector_store"] == "healthy"
    assert report["retrieval"] == "healthy"
    assert report["generation"] == "healthy"
    assert report["citation"] == "healthy"
    assert report["overall_status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_failure():
    """Verify that a failure in one of the health checks raises ProviderHealthFailure containing status report."""
    file_storage = MockFileStorage(exists_flag=True)
    parser_factory = MagicMock()
    parser_factory._pdf_parser = MagicMock()
    parser_factory._docx_parser = MagicMock()
    
    emb_provider = MagicMock()
    emb_provider.health_check = AsyncMock(return_value=True)
    
    vs_service = MagicMock()
    vs_service.health_check = AsyncMock(return_value={"status": "healthy"})
    
    ret_service = MagicMock()
    ret_service._embedding_provider = emb_provider
    ret_service._vector_store_service = vs_service
    
    # LLM provider is down
    llm_provider = MagicMock()
    llm_provider.health_check = AsyncMock(return_value=False)
    gen_service = MagicMock()
    gen_service.provider = llm_provider
    
    pipeline = RAGPipelineService(
        document_repo=MagicMock(),
        upload_use_case=MagicMock(),
        process_document_use_case=MagicMock(),
        retrieval_service=ret_service,
        generation_service=gen_service,
        citation_service=MagicMock(),
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=vs_service,
    )
    
    with pytest.raises(ProviderHealthFailure) as exc:
        await pipeline.health_check()
    
    report = exc.value.report
    assert report["upload_service"] == "healthy"
    assert report["generation"] == "unhealthy"
    assert report["overall_status"] == "unhealthy"
