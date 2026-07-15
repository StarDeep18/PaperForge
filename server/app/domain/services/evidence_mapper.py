"""
Evidence Mapper.

Maps retrieved document chunks into standardized EvidenceReference entities,
preserving ranking order, similarity metrics, and metadata context.
"""

from typing import Optional
from app.core.config import get_settings
from app.domain.entities.chunk import Chunk
from app.domain.entities.retrieval import RetrievalResult
from app.domain.entities.citation import EvidenceReference
from app.domain.exceptions import EmptyEvidence, EvidenceMappingError


class EvidenceMapper:
    """
    Transforms vector database chunks into structured evidence references for citation generation.
    """

    def map_retrieval_result(
        self,
        retrieval_result: Optional[RetrievalResult],
        max_snippet_length: Optional[int] = None,
    ) -> list[EvidenceReference]:
        """
        Map a RetrievalResult's chunks to a list of EvidenceReferences.

        Args:
            retrieval_result: The raw retrieval results from the vector database.
            max_snippet_length: Max character length of the generated snippet context.

        Returns:
            A list of EvidenceReference objects mapped in order.

        Raises:
            EmptyEvidence: If the retrieval result contains no valid chunks.
            EvidenceMappingError: If mapping fails due to malformed data attributes.
        """
        if not retrieval_result or not retrieval_result.retrieved_chunks:
            raise EmptyEvidence()

        settings = get_settings()
        snippet_limit = max_snippet_length or settings.citation_max_snippet_length

        evidence_references = []
        for idx, chunk in enumerate(retrieval_result.retrieved_chunks):
            try:
                # ── 1. Similarity Score extraction ────────────────────
                score = chunk.metadata.get("score")
                if score is None:
                    score = chunk.metadata.get("similarity")
                if score is None:
                    score = chunk.metadata.get("similarity_score")
                
                # Check inspector diagnostics lists as a fallback
                if score is None and retrieval_result.inspector:
                    inspector = retrieval_result.inspector
                    if inspector.retrieved_chunk_ids and chunk.id in inspector.retrieved_chunk_ids:
                        try:
                            s_idx = inspector.retrieved_chunk_ids.index(chunk.id)
                            score = inspector.similarity_scores[s_idx]
                        except (ValueError, IndexError):
                            pass
                
                # Fallback to rank-based scoring if score is completely missing
                if score is None:
                    score = max(0.1, 1.0 - (idx * 0.1))
                
                # Ensure it is float
                similarity_score = float(score)

                # ── 2. Snippet truncation ─────────────────────────────
                content = chunk.content or ""
                if len(content) > snippet_limit:
                    snippet = content[:snippet_limit].strip() + "..."
                else:
                    snippet = content

                # ── 3. Document Title parsing ─────────────────────────
                doc_title = chunk.metadata.get("title") or chunk.metadata.get("document_title")
                if not doc_title:
                    # Fallback to document ID file name without directories
                    doc_id = chunk.document_id or "Unknown Document"
                    doc_title = doc_id.split("/")[-1].split("\\")[-1]

                evidence = EvidenceReference(
                    chunk_id=chunk.id,
                    parent_chunk_id=chunk.parent_chunk_id,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_header,
                    similarity_score=similarity_score,
                    confidence=similarity_score,  # Scorer will overwrite this
                    snippet=snippet,
                )
                evidence_references.append(evidence)

            except Exception as e:
                raise EvidenceMappingError(f"Failed to map chunk '{getattr(chunk, 'id', 'unknown')}': {e}") from e

        return evidence_references
