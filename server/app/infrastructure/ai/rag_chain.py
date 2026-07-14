"""
RAG Chain.

Orchestrates the Retrieval-Augmented Generation pipeline:
1. Embed the user's query
2. Retrieve relevant chunks from the vector store
3. Assemble context with source metadata
4. Generate a citation-aware response via the LLM

This is the core intelligence engine of PaperForge.
"""

from typing import AsyncIterator, Optional

from app.core.logging import logger
from app.domain.entities.chunk import SearchResult
from app.domain.entities.conversation import Citation, Message, MessageRole
from app.domain.repositories.vector_store import VectorStore
from app.infrastructure.ai.embedding_provider import EmbeddingProvider
from app.infrastructure.ai.llm_provider import LLMProvider

# ── Prompt Templates ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are PaperForge, an expert AI research assistant. Your role is to help researchers understand, analyze, and synthesize academic papers.

## Rules
1. Answer questions based ONLY on the provided source material. If the sources don't contain the answer, say so clearly.
2. ALWAYS cite your sources using the format [Source N] where N corresponds to the source numbers provided.
3. Be precise, thorough, and academically rigorous.
4. When comparing information across sources, note agreements and disagreements.
5. Preserve technical terminology and mathematical notation from the original papers.
6. If asked about methodology, provide specific details from the papers.

## Source Material
{context}

## Important
- Every factual claim must have a [Source N] citation
- Synthesize across sources when multiple are relevant
- Note when sources disagree or present different perspectives
- If the question cannot be answered from the sources, state this clearly"""

SOURCE_TEMPLATE = """[Source {index}]
Document: {title}
{page_info}
{section_info}
Content:
{content}
"""


class RAGChain:
    """
    Retrieval-Augmented Generation pipeline.

    Combines vector search with LLM generation to produce
    citation-aware responses grounded in the user's documents.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
    ):
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._llm_provider = llm_provider

    async def query(
        self,
        question: str,
        document_ids: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
        chat_history: Optional[list[dict[str, str]]] = None,
        top_k: int = 8,
    ) -> tuple[str, list[Citation]]:
        """
        Execute a RAG query and return a citation-aware response.

        Args:
            question: The user's question.
            document_ids: Optional document IDs to scope the search.
            collection_id: Optional collection ID to scope the search.
            chat_history: Optional conversation history for context.
            top_k: Number of chunks to retrieve.

        Returns:
            Tuple of (response_text, citations).
        """
        # Step 1: Embed the query
        query_embedding = await self._embedding_provider.embed_query(question)

        # Step 2: Retrieve relevant chunks
        search_results = await self._vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_document_ids=document_ids,
            filter_collection_id=collection_id,
        )

        if not search_results:
            return (
                "I couldn't find relevant information in the uploaded papers to answer this question. "
                "Please make sure the relevant papers are uploaded and try rephrasing your question.",
                [],
            )

        # Step 3: Assemble context
        context = self._build_context(search_results)
        system_prompt = SYSTEM_PROMPT.format(context=context)

        # Step 4: Generate response
        response = await self._llm_provider.generate(
            system_prompt=system_prompt,
            user_message=question,
            chat_history=chat_history,
        )

        # Step 5: Build citations
        citations = self._build_citations(search_results)

        logger.info(
            f"RAG query completed: {len(search_results)} sources, "
            f"{len(citations)} citations"
        )

        return response, citations

    async def query_stream(
        self,
        question: str,
        document_ids: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
        chat_history: Optional[list[dict[str, str]]] = None,
        top_k: int = 8,
    ) -> tuple[AsyncIterator[str], list[Citation]]:
        """
        Execute a RAG query with streaming response.

        Returns citations upfront (from retrieval) and streams
        the LLM response.
        """
        # Step 1-3: Same as non-streaming
        query_embedding = await self._embedding_provider.embed_query(question)
        search_results = await self._vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_document_ids=document_ids,
            filter_collection_id=collection_id,
        )

        citations = self._build_citations(search_results)

        if not search_results:
            async def empty_response():
                yield (
                    "I couldn't find relevant information in the uploaded papers "
                    "to answer this question."
                )
            return empty_response(), []

        context = self._build_context(search_results)
        system_prompt = SYSTEM_PROMPT.format(context=context)

        # Step 4: Stream response
        stream = self._llm_provider.generate_stream(
            system_prompt=system_prompt,
            user_message=question,
            chat_history=chat_history,
        )

        return stream, citations

    def _build_context(self, results: list[SearchResult]) -> str:
        """Format search results into a context string for the LLM."""
        sources = []
        for i, result in enumerate(results, 1):
            page_info = f"Page: {result.page_number}" if result.page_number else ""
            section_info = f"Section: {result.section_header}" if result.section_header else ""

            source = SOURCE_TEMPLATE.format(
                index=i,
                title=result.metadata.get("document_title", f"Document {result.document_id[:8]}"),
                page_info=page_info,
                section_info=section_info,
                content=result.context_text,
            )
            sources.append(source)

        return "\n---\n".join(sources)

    def _build_citations(self, results: list[SearchResult]) -> list[Citation]:
        """Convert search results to Citation entities."""
        citations = []
        seen_chunks = set()

        for result in results:
            # Deduplicate by content hash
            content_key = f"{result.document_id}:{result.content[:100]}"
            if content_key in seen_chunks:
                continue
            seen_chunks.add(content_key)

            citations.append(
                Citation(
                    document_id=result.document_id,
                    document_title=result.metadata.get(
                        "document_title", f"Document {result.document_id[:8]}"
                    ),
                    page_number=result.page_number,
                    section=result.section_header,
                    chunk_text=result.content[:500],  # Truncate for storage
                    relevance_score=result.score,
                )
            )

        return citations
