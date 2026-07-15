"""
LLM Provider Interface.

Defines the contract for all Large Language Model providers.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from app.domain.entities.generation import ProviderResponse


class LLMProvider(ABC):
    """
    Abstract interface for interacting with LLM providers.

    Enables pluggable model providers (Gemini, Claude, OpenAI, local, etc.)
    without affecting application/domain layer logic.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the LLM provider (e.g., 'gemini')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name."""
        pass

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """
        Generate a complete response for the given prompts.

        Args:
            system_prompt: Injected developer/system instruction.
            user_prompt: Injected user query/prompt content.
            chat_history: List of past messages for conversation context.
            options: Dict of generation options (temperature, max_tokens, etc.)

        Returns:
            ProviderResponse containing generated text and token diagnostics.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream response tokens as they are generated.

        Args:
            system_prompt: Injected developer/system instruction.
            user_prompt: Injected user query/prompt content.
            chat_history: List of past messages for conversation context.
            options: Dict of generation options.

        Yields:
            ProviderResponse chunks with incremental text and metadata.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM provider is available and responding.

        Returns:
            True if healthy, False otherwise.
        """
        pass
