"""
LLM Provider.

Wraps the Google Gemini LLM via LangChain for text generation.
Provides both synchronous and streaming interfaces.
"""

from typing import AsyncIterator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.exceptions import LLMError


class LLMProvider:
    """
    Google Gemini LLM wrapper via LangChain.

    Provides a clean interface for text generation with
    both standard and streaming response modes.
    """

    def __init__(self):
        settings = get_settings()
        self._model = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            max_output_tokens=4096,
            convert_system_message_to_human=True,
        )
        self._streaming_model = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
            max_output_tokens=4096,
            streaming=True,
            convert_system_message_to_human=True,
        )
        logger.info(f"LLM provider initialized: model={settings.llm_model}")

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System instruction for the LLM.
            user_message: The user's query.
            chat_history: Optional list of prior messages [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            The LLM's response text.
        """
        try:
            messages = self._build_messages(system_prompt, user_message, chat_history)
            response = await self._model.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise LLMError(str(e)) from e

    async def generate_stream(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a response from the LLM token by token.

        Args:
            system_prompt: System instruction for the LLM.
            user_message: The user's query.
            chat_history: Optional prior messages.

        Yields:
            String chunks as they are generated.
        """
        try:
            messages = self._build_messages(system_prompt, user_message, chat_history)
            async for chunk in self._streaming_model.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            raise LLMError(str(e)) from e

    def _build_messages(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> list:
        """Build the message list for the LLM call."""
        messages = [SystemMessage(content=system_prompt)]

        if chat_history:
            for msg in chat_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))
        return messages
