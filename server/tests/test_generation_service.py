"""
Unit Tests for Generation Layer.

Tests the PromptBuilder, PromptTemplateRegistry, ContextAssembler, TokenizerService,
ResponseValidator, LLM Providers, and GenerationService orchestration.
"""

import pytest
import asyncio
from app.core.config import get_settings
from app.domain.entities.chunk import Chunk
from app.domain.entities.retrieval import RetrievalResult
from app.domain.entities.generation import GenerationRequest, GenerationResult
from app.domain.exceptions import (
    GenerationError,
    GenerationTimeout,
    ProviderUnavailable,
    PromptTooLarge,
    EmptyGeneration,
    ResponseValidationFailed,
)
from app.domain.services.prompt_template import (
    PromptTemplateRegistry,
    prompt_template_registry,
    DefaultRAGPromptTemplate,
    SummarizationPromptTemplate,
    QuizPromptTemplate,
)
from app.domain.services.context_assembler import ContextAssembler
from app.domain.services.tokenizer_service import CharacterLengthTokenizerService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.generation_service import GenerationService
from app.infrastructure.ai.mock_llm_provider import MockLLMProvider


@pytest.fixture
def dummy_retrieval_result() -> RetrievalResult:
    """Fixture returning a standard RetrievalResult with mocked chunks."""
    chunks = [
        Chunk(
            id="chunk-1",
            document_id="paper-1.pdf",
            content="This is the first paragraph discussing quantum computing basics.",
            parent_content="Quantum computing uses quantum mechanics to process information. This is the first paragraph discussing quantum computing basics.",
            page_number=1,
            section_header="Introduction",
        ),
        Chunk(
            id="chunk-2",
            document_id="paper-1.pdf",
            content="Qubits can represent a 0, 1, or superposition of both.",
            parent_content="Unlike classical bits, qubits can represent a 0, 1, or superposition of both. This enables parallel computation.",
            page_number=2,
            section_header="Architecture",
        ),
    ]
    return RetrievalResult(
        query="Explain qubits",
        retrieved_chunks=chunks,
        total_chunks=2,
        retrieval_duration=12.5,
    )


# ── 1. Configuration Tests ───────────────────────────────────────────


def test_generation_configuration():
    """Verify configuration settings load with expected defaults."""
    settings = get_settings()
    assert hasattr(settings, "llm_provider")
    assert hasattr(settings, "llm_model")
    assert hasattr(settings, "llm_temperature")
    assert hasattr(settings, "llm_max_output_tokens")
    assert hasattr(settings, "llm_timeout")
    assert hasattr(settings, "llm_retry_count")
    assert hasattr(settings, "llm_max_prompt_tokens")
    assert settings.llm_provider in ("gemini", "mock")


# ── 2. Prompt Construction, Assembler, and Tokenizer Tests ───────────


def test_context_assembler_assembly(dummy_retrieval_result):
    """Verify that ContextAssembler correctly consolidates parent contents."""
    assembler = ContextAssembler()
    context = assembler.assemble_context(dummy_retrieval_result)
    assert "[1] Source: paper-1.pdf, Page 1, Section: Introduction" in context
    assert "Quantum computing uses quantum mechanics to process information" in context
    assert "[2] Source: paper-1.pdf, Page 2, Section: Architecture" in context
    assert "superposition of both" in context


def test_tokenizer_service_size_estimation():
    """Verify tokenizer estimates size accurately based on character heuristics."""
    tokenizer = CharacterLengthTokenizerService()
    assert tokenizer.estimate_tokens("") == 0
    assert tokenizer.estimate_tokens("abcd") == 1
    assert tokenizer.estimate_tokens("abcdefgh") == 2


def test_prompt_builder_integration(dummy_retrieval_result):
    """Verify that PromptBuilder builds prompts delegating to tokenizer and assembler."""
    template = DefaultRAGPromptTemplate()
    assembler = ContextAssembler()
    tokenizer = CharacterLengthTokenizerService()
    builder = PromptBuilder(template, assembler, tokenizer)
    
    sys_prompt, user_prompt = builder.build_prompts("Query", dummy_retrieval_result)
    assert "scientific literature review" in sys_prompt
    assert "Context from retrieved literature" in user_prompt
    assert builder.estimate_tokens("abcd") == 1


def test_prompt_templates_registry():
    """Verify PromptTemplateRegistry resolves templates correctly."""
    registry = prompt_template_registry
    
    rag = registry.get("default_rag")
    assert isinstance(rag, DefaultRAGPromptTemplate)
    
    quiz = registry.get("quiz")
    assert isinstance(quiz, QuizPromptTemplate)
    
    none_template = registry.get("non-existent-template-xyz")
    assert none_template is None


def test_prompt_templates_interchangeability(dummy_retrieval_result):
    """Test that specialized templates format system instructions and user queries appropriately."""
    assembler = ContextAssembler()
    tokenizer = CharacterLengthTokenizerService()

    # RAG Template
    rag_template = DefaultRAGPromptTemplate()
    rag_builder = PromptBuilder(rag_template, assembler, tokenizer)
    sys_prompt, user_prompt = rag_builder.build_prompts("Explain qubits", dummy_retrieval_result)
    assert "scientific literature review" in sys_prompt
    assert "User Query: Explain qubits" in user_prompt

    # Summarization Template
    sum_template = SummarizationPromptTemplate()
    sum_builder = PromptBuilder(sum_template, assembler, tokenizer)
    sys_prompt, user_prompt = sum_builder.build_prompts("Summarize details", dummy_retrieval_result)
    assert "scientific summarization" in sys_prompt
    assert "Text to summarize" in user_prompt

    # Quiz Template
    quiz_template = QuizPromptTemplate()
    quiz_builder = PromptBuilder(quiz_template, assembler, tokenizer)
    sys_prompt, user_prompt = quiz_builder.build_prompts("Make 3 questions", dummy_retrieval_result)
    assert "academic assessor" in sys_prompt
    assert "Quiz topic/options: Make 3 questions" in user_prompt


# ── 3. Response Validator Tests ──────────────────────────────────────


def test_response_validator_success():
    """Test that valid responses produce no errors and collect correct warnings."""
    validator = ResponseValidator(max_length=500)
    warnings = validator.validate(
        text="The quantum state can be in superposition. [1]",
        provider="mock",
        model="mock-model",
    )
    assert len(warnings) == 0


def test_response_validator_empty():
    """Test that empty or whitespace-only response raises EmptyGeneration."""
    validator = ResponseValidator()
    with pytest.raises(EmptyGeneration) as exc:
        validator.validate("", provider="mock", model="mock-model")
    assert "returned an empty response" in str(exc.value)


def test_response_validator_oversized():
    """Test response exceeding configured size boundary raises ResponseValidationFailed."""
    validator = ResponseValidator(max_length=10)
    with pytest.raises(ResponseValidationFailed) as exc:
        validator.validate("This is longer than 10 characters.", provider="mock", model="mock-model")
    assert "exceeds the configured maximum limit" in str(exc.value)


def test_response_validator_unsafe_formatting():
    """Test unbalanced format triggers structural warnings."""
    validator = ResponseValidator()
    warnings = validator.validate(
        text="Here is some code: ```python print('unclosed block')",
        provider="mock",
        model="mock-model",
    )
    assert any("Unclosed markdown code block" in w for w in warnings)


def test_response_validator_missing_required_fields():
    """Test ResponseValidationFailed is raised when required keywords are missing."""
    validator = ResponseValidator()
    with pytest.raises(ResponseValidationFailed) as exc:
        validator.validate(
            text="This is a simple answer without the key terms.",
            provider="mock",
            model="mock-model",
            required_fields=["superposition"],
        )
    assert "missing required term/field" in str(exc.value)


# ── 4. Mock Provider Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_provider_generation():
    """Test that MockLLMProvider generates configured responses correctly."""
    provider = MockLLMProvider(default_response="Custom mock output text")
    res = await provider.generate("sys", "user")
    assert res.response_text == "Custom mock output text"
    assert res.prompt_tokens > 0
    assert res.response_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_streaming():
    """Verify MockLLMProvider streams chunks correctly."""
    provider = MockLLMProvider(default_response="A B C")
    chunks = []
    async for chunk in provider.generate_stream("sys", "user"):
        chunks.append(chunk.response_text)
    assert "".join(chunks).strip() == "A B C"


# ── 5. Generation Service Orchestration Tests ─────────────────────────


@pytest.mark.asyncio
async def test_generation_service_success(dummy_retrieval_result):
    """Verify end-to-end orchestration success with provider, builder, and validator."""
    provider = MockLLMProvider(default_response="Quantum qubits exist in superposition.")
    validator = ResponseValidator()
    service = GenerationService(provider, validator)

    request = GenerationRequest(
        user_query="Explain qubits",
        retrieval_result=dummy_retrieval_result,
        generation_options={"required_fields": ["qubits"]},
    )
    
    result = await service.generate(request)
    assert isinstance(result, GenerationResult)
    assert result.response == "Quantum qubits exist in superposition."
    assert result.provider == "mock"
    assert result.model == "mock-model"
    
    # Nested Metrics
    assert result.metrics.duration > 0.0
    assert result.metrics.prompt_tokens_estimated > 0
    assert result.metrics.response_tokens_estimated > 0
    assert result.metrics.retry_count == 0
    assert result.metrics.context_size_chars > 0

    # Prompt Inspector
    assert result.inspector.template_used == "default_rag"
    assert "Explain qubits" in result.inspector.user_prompt
    assert "scientific literature review" in result.inspector.system_instruction
    assert result.inspector.estimated_tokens > 0
    assert result.inspector.context_size_chars > 0
    assert result.inspector.generation_time > 0.0

    assert len(result.warnings) == 0


@pytest.mark.asyncio
async def test_generation_service_with_template_name_option(dummy_retrieval_result):
    """Verify that template selection from registry by name options works."""
    provider = MockLLMProvider(default_response="This is a mock quiz answer.")
    validator = ResponseValidator()
    service = GenerationService(provider, validator)

    request = GenerationRequest(
        user_query="Make a quiz",
        retrieval_result=dummy_retrieval_result,
        generation_options={"template_name": "quiz"},
    )
    result = await service.generate(request)
    assert result.inspector.template_used == "quiz"
    assert "Quiz topic/options: Make a quiz" in result.inspector.user_prompt


@pytest.mark.asyncio
async def test_generation_service_provider_unavailable(dummy_retrieval_result):
    """Test that connection failures in provider translate to ProviderUnavailable."""
    provider = MockLLMProvider(
        should_fail_with=ProviderUnavailable("mock", "Downtime simulated")
    )
    service = GenerationService(provider, ResponseValidator())
    
    request = GenerationRequest(user_query="Query", retrieval_result=dummy_retrieval_result)
    with pytest.raises(ProviderUnavailable) as exc:
        await service.generate(request)
    assert "Provider 'mock' is unavailable: Downtime simulated" in str(exc.value)


@pytest.mark.asyncio
async def test_generation_service_timeout(dummy_retrieval_result):
    """Verify timeout exception triggers GenerationTimeout."""
    provider = MockLLMProvider(should_timeout=True, delay=0.1)
    service = GenerationService(provider, ResponseValidator())

    request = GenerationRequest(
        user_query="Query",
        retrieval_result=dummy_retrieval_result,
        generation_options={"retry_count": 0, "timeout": 0.01},
    )
    with pytest.raises(GenerationTimeout) as exc:
        await service.generate(request)
    assert "timed out after" in str(exc.value)


@pytest.mark.asyncio
async def test_generation_service_prompt_too_large(dummy_retrieval_result):
    """Test prompt exceeding strict token boundaries throws PromptTooLarge."""
    provider = MockLLMProvider()
    service = GenerationService(provider, ResponseValidator())

    request = GenerationRequest(
        user_query="Query",
        retrieval_result=dummy_retrieval_result,
        generation_options={"max_prompt_tokens": 10},  # Aggressively low budget
    )
    with pytest.raises(PromptTooLarge) as exc:
        await service.generate(request)
    assert "exceeds limit of 10" in str(exc.value)


@pytest.mark.asyncio
async def test_generation_service_validation_failure(dummy_retrieval_result):
    """Verify validation exceptions block generation and bubble up properly."""
    provider = MockLLMProvider(default_response="No mention of the target word.")
    service = GenerationService(provider, ResponseValidator())

    request = GenerationRequest(
        user_query="Query",
        retrieval_result=dummy_retrieval_result,
        generation_options={"required_fields": ["qubits"]},
    )
    with pytest.raises(ResponseValidationFailed) as exc:
        await service.generate(request)
    assert "missing required term/field 'qubits'" in str(exc.value)
