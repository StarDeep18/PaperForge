"""
Mock LLM Provider.

Used for offline execution, debugging, and unit testing.
"""

import asyncio
from typing import Any, AsyncIterator, Optional
from app.domain.entities.generation import ProviderResponse
from app.domain.services.llm_provider import LLMProvider
from app.domain.exceptions import (
    GenerationError,
    GenerationTimeout,
    ProviderUnavailable,
)


class MockLLMProvider(LLMProvider):
    """
    Mock implementation of LLMProvider for testing purposes.
    """

    def __init__(
        self,
        default_response: str = "This is a mock LLM response based on the provided literature context.",
        provider_name: str = "mock",
        model_name: str = "mock-model",
        delay: float = 0.0,
        should_fail_with: Optional[Exception] = None,
        should_timeout: bool = False,
    ):
        self._default_response = default_response
        self._provider_name = provider_name
        self._model_name = model_name
        self._delay = delay
        self._should_fail_with = should_fail_with
        self._should_timeout = should_timeout

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Simulate LLM generation."""
        if self._should_timeout:
            await asyncio.sleep(self._delay or 1.0)
            raise GenerationTimeout(self._provider_name, 0.5)

        if self._should_fail_with:
            raise self._should_fail_with

        if self._delay > 0:
            await asyncio.sleep(self._delay)

        response_text = self._default_response
        if options and "custom_response" in options:
            response_text = options["custom_response"]

        # Calculate pseudo tokens
        prompt_text = system_prompt + user_prompt
        prompt_tokens = len(prompt_text) // 4
        response_tokens = len(response_text) // 4

        return ProviderResponse(
            response_text=response_text,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            metadata={"mock": True},
        )

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[ProviderResponse]:
        """Simulate LLM streaming."""
        if self._should_timeout:
            await asyncio.sleep(self._delay or 0.1)
            raise GenerationTimeout(self._provider_name, 0.5)

        if self._should_fail_with:
            raise self._should_fail_with

        response_text = self._default_response
        if options and "custom_response" in options:
            response_text = options["custom_response"]

        words = response_text.split(" ")
        for i, word in enumerate(words):
            if self._delay > 0:
                await asyncio.sleep(self._delay / len(words))
            
            chunk_text = (word + " ") if i < len(words) - 1 else word
            yield ProviderResponse(
                response_text=chunk_text,
                prompt_tokens=0,
                response_tokens=len(chunk_text) // 4,
                metadata={"mock": True, "chunk_index": i},
            )

    async def health_check(self) -> bool:
        return self._should_fail_with is None
