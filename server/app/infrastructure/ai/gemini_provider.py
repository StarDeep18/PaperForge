"""
Gemini LLM Provider.

Integrates Google Gemini models via LangChain, implementing LLMProvider,
with error mapping, retries, and timeout constraints.
"""

import asyncio
from typing import Any, AsyncIterator, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.generation import ProviderResponse
from app.domain.exceptions import (
    GenerationError,
    GenerationTimeout,
    ProviderUnavailable,
)
from app.domain.services.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    """
    Adapter for Google Gemini LLM API via LangChain.
    """

    def __init__(self):
        settings = get_settings()
        self._provider_name = "gemini"
        self._model_name = settings.llm_model
        self._api_key = settings.google_api_key
        logger.info(f"GeminiProvider initialized with model: {self._model_name}")

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_client(self, options: Optional[dict[str, Any]] = None, streaming: bool = False) -> ChatGoogleGenerativeAI:
        """
        Build a configured ChatGoogleGenerativeAI client.
        """
        settings = get_settings()
        options = options or {}

        temperature = options.get("temperature", settings.llm_temperature)
        max_tokens = options.get("max_output_tokens", settings.llm_max_output_tokens)

        return ChatGoogleGenerativeAI(
            model=self._model_name,
            google_api_key=self._api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            streaming=streaming,
            convert_system_message_to_human=True,
        )

    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> list:
        """Build LangChain message structure."""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        if chat_history:
            for msg in chat_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role in ("assistant", "ai"):
                    messages.append(AIMessage(content=content))
                else:
                    # Default/fallback
                    messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=user_prompt))
        return messages

    def _translate_exception(self, e: Exception) -> Exception:
        """Map standard exception to domain exceptions."""
        err_msg = str(e).lower()
        if isinstance(e, asyncio.TimeoutError):
            return GenerationTimeout(self.provider_name, get_settings().llm_timeout)
        elif "api_key" in err_msg or "apikey" in err_msg or "unauthorized" in err_msg:
            return ProviderUnavailable(self.provider_name, f"Authentication failed: {e}")
        elif "connection" in err_msg or "dns" in err_msg or "unavailable" in err_msg or "unreachable" in err_msg or "quota" in err_msg or "limit" in err_msg or "429" in err_msg:
            return ProviderUnavailable(self.provider_name, f"API Unavailable/Quota limit hit: {e}")
        return GenerationError(f"Gemini API failed: {e}")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        settings = get_settings()
        timeout = settings.llm_timeout
        retries = settings.llm_retry_count
        backoff = 1.0

        messages = self._build_messages(system_prompt, user_prompt, chat_history)
        client = self._get_client(options, streaming=False)

        last_error = None
        for attempt in range(retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.ainvoke(messages),
                    timeout=timeout
                )
                
                text = response.content if response else ""
                
                # Estimate tokens
                prompt_text = system_prompt + user_prompt
                prompt_tokens = len(prompt_text) // 4
                response_tokens = len(text) // 4

                # Extract metadata if available
                metadata = {}
                if hasattr(response, "response_metadata") and response.response_metadata:
                    metadata = dict(response.response_metadata)

                return ProviderResponse(
                    response_text=text,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    metadata=metadata,
                )
            except Exception as e:
                last_error = self._translate_exception(e)
                logger.warning(
                    f"Gemini LLM generate attempt {attempt + 1}/{retries + 1} failed: {e}"
                )
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0

        raise last_error or GenerationError("Gemini generation failed after retries")

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[ProviderResponse]:
        messages = self._build_messages(system_prompt, user_prompt, chat_history)
        client = self._get_client(options, streaming=True)

        try:
            async for chunk in client.astream(messages):
                text = chunk.content if chunk else ""
                # Stream each chunk
                yield ProviderResponse(
                    response_text=text,
                    prompt_tokens=0,  # Intermediate chunk doesn't count total prompt tokens
                    response_tokens=len(text) // 4,
                    metadata=dict(chunk.response_metadata) if hasattr(chunk, "response_metadata") and chunk.response_metadata else {},
                )
        except Exception as e:
            logger.error(f"Gemini LLM streaming failed: {e}")
            raise self._translate_exception(e)

    async def health_check(self) -> bool:
        """Perform a quick health check with a low timeout."""
        try:
            client = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=0.1,
                max_output_tokens=5,
            )
            # Low timeout (5s) for check
            await asyncio.wait_for(
                client.ainvoke([HumanMessage(content="ping")]),
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.error(f"Gemini LLM Provider health check failed: {e}")
            return False
