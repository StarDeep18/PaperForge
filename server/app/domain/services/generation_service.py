"""
Generation Service.

Business orchestration service managing the generation layer.
"""

import time
import asyncio
from typing import Any, Optional
from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.generation import (
    GenerationRequest,
    GenerationResult,
    GenerationMetrics,
    PromptInspector,
)
from app.domain.exceptions import GenerationError, PromptTooLarge
from app.domain.services.llm_provider import LLMProvider
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.prompt_template import (
    PromptTemplate,
    PromptTemplateRegistry,
    prompt_template_registry,
)
from app.domain.services.context_assembler import ContextAssembler
from app.domain.services.tokenizer_service import (
    TokenizerService,
    CharacterLengthTokenizerService,
)
from app.domain.services.response_validator import ResponseValidator


class GenerationService:
    """
    Orchestrates prompt construction, model provider invocation, output validation,
    timing, structured logging, and unified response building.
    """

    def __init__(
        self,
        provider: LLMProvider,
        response_validator: ResponseValidator,
        context_assembler: Optional[ContextAssembler] = None,
        tokenizer: Optional[TokenizerService] = None,
        registry: Optional[PromptTemplateRegistry] = None,
    ):
        self._provider = provider
        self._response_validator = response_validator
        self._context_assembler = context_assembler or ContextAssembler()
        self._tokenizer = tokenizer or CharacterLengthTokenizerService()
        self._registry = registry or prompt_template_registry

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def context_assembler(self) -> ContextAssembler:
        return self._context_assembler

    @property
    def tokenizer(self) -> TokenizerService:
        return self._tokenizer

    @property
    def registry(self) -> PromptTemplateRegistry:
        return self._registry

    async def generate(
        self,
        request: GenerationRequest,
        template: Optional[PromptTemplate] = None,
    ) -> GenerationResult:
        """
        Orchestrate prompt generation, provider execution, validation, and diagnostics.

        Args:
            request: Injected GenerationRequest details.
            template: Optional prompt template override.

        Returns:
            A populated GenerationResult with nested metrics and prompt inspector details.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        warnings = []

        # ── 1. Select Prompt Template via Registry ────────────────────
        active_template = template
        if not active_template:
            opt_template = request.generation_options.get("template")
            if isinstance(opt_template, PromptTemplate):
                active_template = opt_template
            else:
                template_name = request.generation_options.get("template_name", "default_rag")
                active_template = self._registry.get(template_name) or self._registry.get("default_rag")

        # ── 2. Prompt Builder Setup ──────────────────────────────────
        builder = PromptBuilder(
            template=active_template,
            context_assembler=self._context_assembler,
            tokenizer=self._tokenizer,
        )

        # ── 3. Build Prompts ──────────────────────────────────────────
        system_prompt, user_prompt = builder.build_prompts(
            query=request.user_query,
            retrieval_result=request.retrieval_result,
            history=request.conversation_history,
        )

        # ── 4. Token & Context Size Diagnostics ───────────────────────
        context_str = self._context_assembler.assemble_context(request.retrieval_result)
        context_size_chars = len(context_str)

        prompt_text = system_prompt + user_prompt
        prompt_tokens_est = builder.estimate_tokens(prompt_text)

        max_prompt_tokens = request.generation_options.get(
            "max_prompt_tokens", settings.llm_max_prompt_tokens
        )
        if prompt_tokens_est > max_prompt_tokens:
            logger.error(
                f"Generation failed: Prompt size ({prompt_tokens_est} tokens) "
                f"exceeded configured budget ({max_prompt_tokens} tokens)."
            )
            raise PromptTooLarge(size=prompt_tokens_est, limit=max_prompt_tokens)

        # ── 5. Call LLM Provider with Retries ─────────────────────────
        retry_count = request.generation_options.get(
            "retry_count", settings.llm_retry_count
        )
        options = {
            "temperature": request.generation_options.get(
                "temperature", settings.llm_temperature
            ),
            "max_output_tokens": request.generation_options.get(
                "max_output_tokens", settings.llm_max_output_tokens
            ),
            "timeout": request.generation_options.get(
                "timeout", settings.llm_timeout
            ),
            **request.generation_options,
        }

        last_error = None
        provider_response = None
        retry_attempts_used = 0

        for attempt in range(retry_count + 1):
            try:
                provider_response = await self._provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    chat_history=request.conversation_history,
                    options=options,
                )
                retry_attempts_used = attempt
                break
            except Exception as e:
                last_error = e
                retry_attempts_used = attempt
                logger.warning(
                    f"Generation Service execution attempt {attempt + 1}/{retry_count + 1} "
                    f"failed for provider '{self._provider.provider_name}': {e}"
                )
                if attempt < retry_count:
                    # Simple backoff delay
                    await asyncio.sleep(1.0 * (2.0 ** attempt))

        if not provider_response:
            logger.error(
                f"Generation Service execution failed after {retry_count + 1} attempts. "
                f"Last Error: {last_error}"
            )
            raise last_error or GenerationError("Generation failed after exhaustion of retries")

        # ── 6. Response Validation ───────────────────────────────────
        required_fields = request.generation_options.get("required_fields")
        try:
            val_warnings = self._response_validator.validate(
                text=provider_response.response_text,
                provider=self._provider.provider_name,
                model=self._provider.model_name,
                required_fields=required_fields,
            )
            warnings.extend(val_warnings)
        except Exception as e:
            logger.error(f"Response validation failed for response: {e}")
            raise

        # ── 7. Metrics & Prompt Inspector ────────────────────────────
        duration = time.perf_counter() - start_time
        response_tokens_est = provider_response.response_tokens or builder.estimate_tokens(
            provider_response.response_text
        )

        metrics = GenerationMetrics(
            duration=duration,
            prompt_tokens_estimated=prompt_tokens_est,
            response_tokens_estimated=response_tokens_est,
            retry_count=retry_attempts_used,
            context_size_chars=context_size_chars,
        )

        inspector = PromptInspector(
            system_instruction=system_prompt,
            user_prompt=user_prompt,
            estimated_tokens=prompt_tokens_est,
            context_size_chars=context_size_chars,
            template_used=active_template.name,
            generation_time=duration,
        )

        # ── 8. Unified Generation Result ─────────────────────────────
        result = GenerationResult(
            response=provider_response.response_text,
            provider=self._provider.provider_name,
            model=self._provider.model_name,
            metrics=metrics,
            inspector=inspector,
            warnings=warnings,
            metadata=provider_response.metadata,
        )

        # ── 9. Structured Logging ─────────────────────────────────────
        logger.info(
            f"Generation layer completed. Provider: '{result.provider}', Model: '{result.model}', "
            f"Duration: {metrics.duration:.2f}s, Prompt Tokens: {metrics.prompt_tokens_estimated}, "
            f"Response Tokens: {metrics.response_tokens_estimated}, Context Size: {metrics.context_size_chars} chars, "
            f"Retries Used: {metrics.retry_count}, Warnings: {len(result.warnings)}"
        )

        return result
