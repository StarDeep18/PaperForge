"""
Prompt Builder.

Handles context assembly from RetrievalResult, applies a PromptTemplate,
and estimates prompt size.
"""

import math
from typing import Optional
from app.domain.entities.retrieval import RetrievalResult
from app.domain.services.prompt_template import PromptTemplate


class PromptBuilder:
    """
    Assembles grounded context and formats the prompt via an interchangeable PromptTemplate.
    """

    def __init__(self, template: PromptTemplate):
        self._template = template

    @property
    def template(self) -> PromptTemplate:
        return self._template

    def assemble_context(self, retrieval_result: Optional[RetrievalResult]) -> str:
        """
        Extract and format textual context from RetrievalResult chunks.
        """
        if not retrieval_result or not retrieval_result.retrieved_chunks:
            return ""

        context_parts = []
        for idx, chunk in enumerate(retrieval_result.retrieved_chunks):
            # Prefer larger context parent_content if available, fall back to content
            content = chunk.parent_content or chunk.content
            doc_id = chunk.document_id or "Unknown Document"
            page_str = f", Page {chunk.page_number}" if chunk.page_number is not None else ""
            section_str = f", Section: {chunk.section_header}" if chunk.section_header else ""
            
            context_parts.append(
                f"[{idx + 1}] Source: {doc_id}{page_str}{section_str}\n"
                f"Content: {content.strip()}"
            )
        
        return "\n\n".join(context_parts)

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
        context = self.assemble_context(retrieval_result)
        system_prompt = self._template.system_instruction
        user_prompt = self._template.format_user_prompt(
            query=query,
            context=context,
            history=history,
        )
        return system_prompt, user_prompt

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count of a string using character length heuristics.
        Standard heuristic: ~4 characters per token.
        """
        if not text:
            return 0
        return math.ceil(len(text) / 4)
