"""
Generation Domain Entities.

Provides structured request and response models for the generation service
and external LLM providers.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from app.domain.entities.retrieval import RetrievalResult


@dataclass
class GenerationRequest:
    """
    Structured generation request parameters.
    """

    user_query: str
    retrieval_result: Optional[RetrievalResult] = None
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    generation_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationMetrics:
    """
    Performance and diagnostic metrics for a single generation call.
    """

    duration: float  # in seconds
    prompt_tokens_estimated: int = 0
    response_tokens_estimated: int = 0
    retry_count: int = 0
    context_size_chars: int = 0


@dataclass
class PromptInspector:
    """
    Diagnostic payload detailing the raw prompts sent to the LLM.
    """

    system_instruction: str
    user_prompt: str
    estimated_tokens: int
    context_size_chars: int
    template_used: str
    generation_time: Optional[float] = None


@dataclass
class GenerationResult:
    """
    Unified payload returned to the application from the generation layer.
    """

    response: str
    provider: str
    model: str
    metrics: GenerationMetrics
    inspector: PromptInspector
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """
    Response returned directly from an LLMProvider implementation.
    """

    response_text: str
    prompt_tokens: int = 0
    response_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
