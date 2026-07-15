"""
Context Assembler.

Assembles textual contexts from retrieved chunks for RAG prompting.
"""

from typing import Optional
from app.domain.entities.retrieval import RetrievalResult


class ContextAssembler:
    """
    Decoupled service for mapping, deduplicating, and formatting RAG context blocks.
    """

    def assemble_context(self, retrieval_result: Optional[RetrievalResult]) -> str:
        """
        Convert retrieved chunks into a formatted textual context block.

        Args:
            retrieval_result: Injected retrieval diagnostics and chunks.

        Returns:
            A joined academic-standard block of source text.
        """
        if not retrieval_result or not retrieval_result.retrieved_chunks:
            return ""

        context_parts = []
        for idx, chunk in enumerate(retrieval_result.retrieved_chunks):
            # Prioritize parent context content, fallback to chunk's own content
            content = chunk.parent_content or chunk.content
            doc_id = chunk.document_id or "Unknown Document"
            page_str = f", Page {chunk.page_number}" if chunk.page_number is not None else ""
            section_str = f", Section: {chunk.section_header}" if chunk.section_header else ""
            
            context_parts.append(
                f"[{idx + 1}] Source: {doc_id}{page_str}{section_str}\n"
                f"Content: {content.strip()}"
            )
        
        return "\n\n".join(context_parts)
