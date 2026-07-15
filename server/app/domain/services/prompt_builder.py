"""
Prompt Builder.

Handles prompt construction via prompt templates, utilizing a ContextAssembler
for grounding and a TokenizerService for sizing checks.
"""

from typing import Optional
from app.domain.entities.retrieval import RetrievalResult
from app.domain.services.prompt_template import PromptTemplate
from app.domain.services.context_assembler import ContextAssembler
from app.domain.services.tokenizer_service import TokenizerService


class PromptBuilder:
    """
    Constructs system instructions and user queries, leveraging ContextAssembler
    and TokenizerService to handle grounding and sizing details.
    """

    def __init__(
        self,
        template: PromptTemplate,
        context_assembler: ContextAssembler,
        tokenizer: TokenizerService,
    ):
        self._template = template
        self._context_assembler = context_assembler
        self._tokenizer = tokenizer

    @property
    def template(self) -> PromptTemplate:
        return self._template

    @property
    def context_assembler(self) -> ContextAssembler:
        return self._context_assembler

    @property
    def tokenizer(self) -> TokenizerService:
        return self._tokenizer

    def build_prompts(
        self,
        query: str,
        retrieval_result: Optional[RetrievalResult],
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str]:
        """
        Construct system instructions and user prompt.

        Returns:
            A tuple of (system_instruction, user_prompt).
        """
        context = self._context_assembler.assemble_context(retrieval_result)
        system_prompt = self._template.system_instruction
        user_prompt = self._template.format_user_prompt(
            query=query,
            context=context,
            history=history,
        )
        return system_prompt, user_prompt

    def estimate_tokens(self, text: str) -> int:
        """
        Delegate token count estimation to the injected TokenizerService.
        """
        return self._tokenizer.estimate_tokens(text)
