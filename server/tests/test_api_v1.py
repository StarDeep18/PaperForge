"""
API v1 REST Endpoints Integration Tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from app.main import create_app
from app.api.dependencies import get_rag_pipeline_service, get_upload_document_use_case, get_current_user_id
from app.domain.entities.document import Document, DocumentStatus, DocumentType, DocumentMetadata
from app.domain.entities.rag import DocumentProcessingResult, RAGResponse
from app.domain.entities.chunk import Chunk
from app.domain.entities.retrieval import RetrievalResult, ContextWindow
from app.domain.entities.generation import GenerationMetrics, PromptInspector
from app.domain.entities.citation import Citation, EvidenceGraph, EvidenceNode, CitationResult
from app.domain.exceptions import (
    DocumentNotFoundError,
    UnsupportedFileTypeError,
    FileTooLargeError,
    DocumentProcessingFailure,
    QuestionAnsweringFailure,
    ProviderHealthFailure,
)

# Create the test client
app = create_app()
client = TestClient(app)


# ── Dependency Overrides and Fixtures ────────────────────────────────

@pytest.fixture
def mock_pipeline_service():
    service = MagicMock()
    # Mocking async methods
    service.ingest_document = AsyncMock()
    service.process_document = AsyncMock()
    service.answer_question = AsyncMock()
    service.health_check = AsyncMock()
    service.list_documents = AsyncMock()
    service.count_documents = AsyncMock()
    service.get_document = AsyncMock()
    service.delete_document = AsyncMock()
    return service


@pytest.fixture
def mock_upload_use_case():
    return MagicMock()


@pytest.fixture(autouse=True)
def apply_dependency_overrides(mock_pipeline_service, mock_upload_use_case):
    # Override composition root dependencies
    app.dependency_overrides[get_rag_pipeline_service] = lambda: mock_pipeline_service
    app.dependency_overrides[get_upload_document_use_case] = lambda: mock_upload_use_case
    app.dependency_overrides[get_current_user_id] = lambda: "user-123"
    yield
    app.dependency_overrides.clear()


# ── Test Cases ───────────────────────────────────────────────────────

def test_documents_upload_success(mock_pipeline_service):
    """Verify that document uploading and parsing synchronously returns processing details."""
    processing_res = DocumentProcessingResult(
        success=True,
        document_id="doc-123-uuid",
        pages=5,
        chunks=12,
        embeddings=12,
        duration=2.54,
        warnings=["Test warning"],
    )
    mock_pipeline_service.ingest_document.return_value = processing_res

    files = [
        ("files", ("paper.pdf", b"PDF dummy content bytes", "application/pdf"))
    ]
    
    response = client.post("/api/v1/documents/upload", files=files, data={"collection_id": "collection-999"})
    
    assert response.status_code == 201
    json_data = response.json()
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert json_data[0]["document_id"] == "doc-123-uuid"
    assert json_data[0]["filename"] == "paper.pdf"
    assert json_data[0]["pages"] == 5
    assert json_data[0]["chunks"] == 12
    assert json_data[0]["processing_time"] == 2.54
    assert "Test warning" in json_data[0]["warnings"]


def test_documents_upload_unsupported_file_type(mock_pipeline_service):
    """Verify that uploading an unsupported file type maps to HTTP 400 and returns consistent JSON error."""
    mock_pipeline_service.ingest_document.side_effect = UnsupportedFileTypeError(".xyz", [".pdf", ".docx", ".txt"])

    files = [
        ("files", ("paper.xyz", b"xyz content", "text/plain"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    
    assert response.status_code == 400
    err_json = response.json()
    assert err_json["error"] == "UnsupportedFileTypeError"
    assert "xyz" in err_json["message"]
    assert err_json["details"] == {"allowed": [".pdf", ".docx", ".txt"]}


def test_documents_upload_file_too_large(mock_pipeline_service):
    """Verify that uploading an oversized file maps to HTTP 413 and returns consistent JSON error."""
    mock_pipeline_service.ingest_document.side_effect = FileTooLargeError(100 * 1024 * 1024, 10 * 1024 * 1024)

    files = [
        ("files", ("huge_paper.pdf", b"huge dummy", "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    
    assert response.status_code == 413
    err_json = response.json()
    assert err_json["error"] == "FileTooLargeError"
    assert "exceeds maximum" in err_json["message"]
    assert err_json["details"]["max_bytes"] == 10 * 1024 * 1024
    assert err_json["details"]["size_bytes"] == 100 * 1024 * 1024


def test_documents_upload_empty_query():
    """Verify that sending a file with no content results in validation error."""
    files = [
        ("files", ("paper.pdf", b"", "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_list_documents(mock_pipeline_service):
    """Verify that listing uploaded documents works and serializes correctly."""
    doc = Document(
        id="doc-777",
        user_id="user-123",
        filename="stored.pdf",
        original_filename="paper.pdf",
        file_path="/path/to/file",
        file_size=5000,
        file_type=DocumentType.PDF,
        status=DocumentStatus.READY,
        metadata=DocumentMetadata(title="Quantum Computation", authors=["Einstein"], page_count=10, word_count=2000),
        collection_id="col-abc",
        chunk_count=22,
    )
    mock_pipeline_service.list_documents.return_value = [doc]
    mock_pipeline_service.count_documents.return_value = 1

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["total"] == 1
    assert res_json["page"] == 1
    assert res_json["size"] == 20
    assert res_json["pages"] == 1

    docs = res_json["items"]
    assert isinstance(docs, list)
    assert len(docs) == 1
    assert docs[0]["id"] == "doc-777"
    assert docs[0]["metadata"]["title"] == "Quantum Computation"
    assert docs[0]["metadata"]["authors"] == ["Einstein"]
    assert docs[0]["collection_id"] == "col-abc"
    assert docs[0]["chunk_count"] == 22


def test_get_document_success(mock_pipeline_service):
    """Verify that retrieving metadata of an existing document returns details successfully."""
    doc = Document(
        id="doc-777",
        user_id="user-123",
        filename="stored.pdf",
        original_filename="paper.pdf",
        file_path="/path/to/file",
        file_size=5000,
        file_type=DocumentType.PDF,
        status=DocumentStatus.READY,
        metadata=DocumentMetadata(title="Quantum Computation", authors=["Einstein"], page_count=10, word_count=2000),
        collection_id="col-abc",
        chunk_count=22,
    )
    mock_pipeline_service.get_document.return_value = doc

    response = client.get("/api/v1/documents/doc-777")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == "doc-777"
    assert json_data["metadata"]["title"] == "Quantum Computation"


def test_get_document_not_found(mock_pipeline_service):
    """Verify that retrieving a non-existent document maps to HTTP 404."""
    mock_pipeline_service.get_document.side_effect = DocumentNotFoundError("doc-999")

    response = client.get("/api/v1/documents/doc-999")
    assert response.status_code == 404
    err_json = response.json()
    assert err_json["error"] == "DocumentNotFoundError"
    assert "Document not found" in err_json["message"]


def test_delete_document_success(mock_pipeline_service):
    """Verify deleting document returns HTTP 204."""
    mock_pipeline_service.delete_document.return_value = None

    response = client.delete("/api/v1/documents/doc-777")
    assert response.status_code == 204
    assert response.text == ""


def test_chat_success(mock_pipeline_service):
    """Verify sending query grounding request successfully calls RAGPipelineService.answer_question."""
    chunk = Chunk(id="chunk-1", document_id="doc-1", content="Superposition basic concepts.")
    ret_res = RetrievalResult(
        query="superposition",
        retrieved_chunks=[chunk],
        total_chunks=1,
    )
    metrics = GenerationMetrics(duration=0.6, prompt_tokens_estimated=30, response_tokens_estimated=20)
    prompt_ins = PromptInspector(system_instruction="sys", user_prompt="user", estimated_tokens=30, context_size_chars=40, template_used="default")
    
    citation = Citation(citation_id="1", document_id="doc-1", document_title="Quantum Review", pages=[1], supporting_chunks=["chunk-1"], confidence="High")
    evidence_graph = EvidenceGraph(nodes=[EvidenceNode(statement="Superposition is key.", supporting_chunks=["chunk-1"], confidence=0.9)])
    
    rag_res = RAGResponse(
        answer="Superposition is key.",
        citations=[citation],
        confidence="High",
        evidence_graph=evidence_graph,
        retrieval_result=ret_res,
        generation_metrics=metrics,
        prompt_inspector=prompt_ins,
        warnings=["Some warn"],
    )
    mock_pipeline_service.answer_question.return_value = rag_res

    payload = {
        "query": "What is superposition?",
        "workspace_id": "ws-123",
        "conversation_history": [{"role": "user", "content": "hi"}],
        "retrieval_options": {"top_k": 3},
        "generation_options": {"temperature": 0.5}
    }
    
    response = client.post("/api/v1/chat", json=payload)
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["answer"] == "Superposition is key."
    assert json_data["confidence"] == "High"
    assert len(json_data["citations"]) == 1
    assert json_data["citations"][0]["document_title"] == "Quantum Review"
    assert json_data["evidence_graph"]["nodes"][0]["statement"] == "Superposition is key."
    assert "Some warn" in json_data["warnings"]


def test_chat_validation_failure_empty_query():
    """Verify that an empty chat query returns HTTP 422 due to Pydantic validator."""
    payload = {
        "query": "   ",
        "workspace_id": "ws-123",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422
    assert "Query cannot be empty" in response.text


def test_chat_validation_failure_invalid_history():
    """Verify that malformed conversation history schema returns HTTP 422."""
    payload = {
        "query": "What is superposition?",
        "conversation_history": [{"role": "bot", "content": "invalid role name"}]
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422
    assert "Role must be one of" in response.text


def test_chat_pipeline_failure(mock_pipeline_service):
    """Verify that general pipeline exceptions map to HTTP 422."""
    mock_pipeline_service.answer_question.side_effect = QuestionAnsweringFailure("Simulated LLM Timeout")

    payload = {
        "query": "What is superposition?",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422
    err_json = response.json()
    assert err_json["error"] == "QuestionAnsweringFailure"
    assert "Simulated LLM Timeout" in err_json["message"]


def test_health_check_success(mock_pipeline_service):
    """Verify that listing pipeline status checks works successfully."""
    report = {
        "upload_service": "healthy",
        "parser": "healthy",
        "embedding_provider": "healthy",
        "vector_store": "healthy",
        "retrieval": "healthy",
        "generation": "healthy",
        "citation": "healthy",
        "overall_status": "healthy",
    }
    mock_pipeline_service.health_check.return_value = report

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["overall_status"] == "healthy"
    assert json_data["vector_store"] == "healthy"


def test_health_check_failure(mock_pipeline_service):
    """Verify that an unhealthy component results in HTTP 503 containing detailed status report."""
    report = {
        "upload_service": "healthy",
        "parser": "healthy",
        "embedding_provider": "healthy",
        "vector_store": "unhealthy",
        "retrieval": "unhealthy",
        "generation": "healthy",
        "citation": "healthy",
        "overall_status": "unhealthy",
    }
    mock_pipeline_service.health_check.side_effect = ProviderHealthFailure("Database is unreachable", report)

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    err_json = response.json()
    assert err_json["error"] == "ProviderHealthFailure"
    assert "unreachable" in err_json["message"]
    assert err_json["details"]["vector_store"] == "unhealthy"


def test_request_id_tracing(mock_pipeline_service):
    """Verify that incoming X-Request-ID headers are traced and returned in responses."""
    mock_pipeline_service.health_check.return_value = {
        "upload_service": "healthy",
        "parser": "healthy",
        "embedding_provider": "healthy",
        "vector_store": "healthy",
        "retrieval": "healthy",
        "generation": "healthy",
        "citation": "healthy",
        "overall_status": "healthy",
    }

    headers = {"X-Request-ID": "test-uuid-999"}
    response = client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-uuid-999"


def test_rate_limiting(mock_pipeline_service):
    """Verify that exceeding rate limits returns HTTP 429 in consistent JSON structure."""
    mock_pipeline_service.answer_question.return_value = RAGResponse(
        answer="Quantum states",
        citations=[],
        confidence="High",
        evidence_graph=EvidenceGraph(nodes=[]),
        retrieval_result=None,
        generation_metrics=None,
        prompt_inspector=None,
        warnings=[],
    )
    payload = {"query": "test query"}

    # We send consecutive requests. In our route, limiter is configured at 5/minute.
    # By the 6th query, it must trigger 429 RateLimitExceeded.
    triggered = False
    for _ in range(10):
        response = client.post("/api/v1/chat", json=payload)
        if response.status_code == 429:
            triggered = True
            err_json = response.json()
            assert err_json["error"] == "RateLimitExceeded"
            assert "Too many requests" in err_json["message"]
            break

    assert triggered, "Expected rate limit (429) to trigger after consecutive requests"


def test_gzip_compression(mock_pipeline_service):
    """Verify that requesting gzip encoding compresses response payload exceeding minimum size."""
    large_report = {
        "upload_service": "healthy",
        "parser": "healthy",
        "embedding_provider": "healthy",
        "vector_store": "healthy",
        "retrieval": "healthy",
        "generation": "healthy",
        "citation": "healthy",
        "overall_status": "healthy" + "A" * 1500,  # Enforce minimum size requirement of 1000 bytes
    }
    mock_pipeline_service.health_check.return_value = large_report

    headers = {"Accept-Encoding": "gzip"}
    response = client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
