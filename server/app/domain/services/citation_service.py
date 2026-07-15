"""
Citation Service.

Business orchestration service managing the citation engine pipeline, segmenting answers,
constructing the internal EvidenceGraph, scoring confidence, and logging metrics.
"""

import re
import time
from typing import Optional
from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.retrieval import RetrievalResult
from app.domain.entities.citation import (
    CitationResult,
    EvidenceReference,
    EvidenceNode,
    EvidenceGraph,
)
from app.domain.exceptions import CitationError, EmptyEvidence
from app.domain.services.evidence_mapper import EvidenceMapper
from app.domain.services.citation_builder import CitationBuilder
from app.domain.services.confidence_scorer import ConfidenceScorer


class CitationService:
    """
    Main entry point for mapping, scoring, consolidating, and auditing grounding citations in answers.
    """

    def __init__(
        self,
        evidence_mapper: Optional[EvidenceMapper] = None,
        citation_builder: Optional[CitationBuilder] = None,
        confidence_scorer: Optional[ConfidenceScorer] = None,
    ):
        self._evidence_mapper = evidence_mapper or EvidenceMapper()
        self._citation_builder = citation_builder or CitationBuilder()
        self._confidence_scorer = confidence_scorer or ConfidenceScorer()

    @property
    def evidence_mapper(self) -> EvidenceMapper:
        return self._evidence_mapper

    @property
    def citation_builder(self) -> CitationBuilder:
        return self._citation_builder

    @property
    def confidence_scorer(self) -> ConfidenceScorer:
        return self._confidence_scorer

    def _segment_answer(self, answer: str) -> list[str]:
        """
        Segment the generated answer text into individual sentences/statements.
        """
        if not answer:
            return []
        
        # Split on sentence terminals followed by space, or newlines
        sentences = re.split(r'(?<=[.!?])\s+|\n+', answer)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_word_tokens(self, text: str) -> set[str]:
        """
        Tokenize text into lowercased alphanumeric words, ignoring small stopwords.
        """
        words = re.findall(r'\b\w{3,}\b', text.lower())
        stopwords = {"the", "and", "for", "this", "that", "with", "from", "was", "were", "are"}
        return set(w for w in words if w not in stopwords)

    def _build_evidence_graph(
        self,
        statements: list[str],
        references: list[EvidenceReference],
    ) -> EvidenceGraph:
        """
        Build the internal EvidenceGraph mapping individual statements to supporting chunks.
        Matches explicit bracket indices (e.g. [1]) or uses word-overlap fallbacks.
        """
        nodes = []
        
        for stmt in statements:
            supporting_chunk_ids = []
            
            # ── 1. Bracket-based check (e.g., matching [1], [2] inside sentence) ──
            matches = re.findall(r'\[(\d+)\]', stmt)
            if matches:
                for match in matches:
                    idx = int(match) - 1
                    if 0 <= idx < len(references):
                        supporting_chunk_ids.append(references[idx].chunk_id)
            
            # ── 2. Fallback text similarity overlap check ────────────────────────
            # If no bracket index is cited, look for common vocabulary matches
            if not supporting_chunk_ids:
                stmt_words = self._extract_word_tokens(stmt)
                if len(stmt_words) >= 3:  # Only evaluate substantial statements
                    best_match_id = None
                    max_overlap = 0
                    
                    for ref in references:
                        ref_words = self._extract_word_tokens(ref.snippet)
                        overlap = len(stmt_words.intersection(ref_words))
                        if overlap > max_overlap and overlap >= 3:
                            max_overlap = overlap
                            best_match_id = ref.chunk_id
                    
                    if best_match_id:
                        supporting_chunk_ids.append(best_match_id)

            # ── 3. Confidence calculation ────────────────────────────────────────
            stmt_conf_scores = [
                ref.confidence for ref in references if ref.chunk_id in supporting_chunk_ids
            ]
            avg_confidence = sum(stmt_conf_scores) / len(stmt_conf_scores) if stmt_conf_scores else 0.0

            nodes.append(EvidenceNode(
                statement=stmt,
                supporting_chunks=supporting_chunk_ids,
                confidence=avg_confidence,
            ))

        return EvidenceGraph(nodes=nodes)

    def generate_citations(
        self,
        answer: str,
        retrieval_result: Optional[RetrievalResult],
        grouping_policy: Optional[str] = None,
        page_merge_policy: Optional[str] = None,
    ) -> CitationResult:
        """
        Orchestrate citation mapping, deduplication, scoring, statement graph build,
        and structured audit logging.

        Args:
            answer: Raw text response generated by the LLM.
            retrieval_result: Grounding source chunks fetched.
            grouping_policy: Optional custom override for document or page grouping.
            page_merge_policy: Optional override for page range merging rules.

        Returns:
            A detailed CitationResult.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        warnings = []

        if not retrieval_result or not retrieval_result.retrieved_chunks:
            logger.error("Citation generation failed: Grounding evidence contains no source chunks.")
            raise EmptyEvidence()

        try:
            # ── 1. Map retrieved chunks to EvidenceReference ──────────────────
            references = self._evidence_mapper.map_retrieval_result(retrieval_result)

            # ── 2. Calculate individual and overall confidence score ──────────
            overall_cat, overall_score = self._confidence_scorer.score_evidence(references)

            # ── 3. Filter low confidence references ───────────────────────────
            min_conf = settings.citation_min_confidence
            filtered_references = []
            for ref in references:
                if ref.confidence < min_conf:
                    msg = (
                        f"Discarded reference chunk '{ref.chunk_id}' from document "
                        f"'{ref.document_id}' due to confidence score ({ref.confidence:.2f}) "
                        f"falling below required threshold {min_conf}."
                    )
                    warnings.append(msg)
                    logger.warning(msg)
                else:
                    filtered_references.append(ref)

            # ── 4. Group, merge pages, and deduplicate Citations ──────────────
            citations = self._citation_builder.build_citations(
                filtered_references,
                grouping_policy=grouping_policy,
                page_merge_policy=page_merge_policy,
            )

            # ── 5. Segment answer and build statement-level Evidence Graph ────
            statements = self._segment_answer(answer)
            evidence_graph = self._build_evidence_graph(statements, references)

            # Calculate diagnostic statistics
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Count unique documents and pages referenced in citations
            referenced_docs = sorted(list(set(c.document_id for c in citations)))
            referenced_pages = sorted(list(set(page for c in citations for page in c.pages)))
            
            # Duplicate removals = total mapped reference chunks minus final formatted citations
            duplicate_removals = max(0, len(references) - len(citations))

            result = CitationResult(
                answer=answer,
                citations=citations,
                evidence=references,
                overall_confidence=overall_cat,
                warnings=warnings,
                evidence_graph=evidence_graph,
            )

            # ── 6. Structured Logging ─────────────────────────────────────────
            logger.info(
                f"Citation Engine completed in {duration_ms:.2f}ms. "
                f"Citations generated: {len(citations)}, "
                f"Documents referenced: {len(referenced_docs)}, "
                f"Pages referenced: {len(referenced_pages)}, "
                f"Overall Confidence: '{overall_cat}' ({overall_score:.2f}), "
                f"Duplicate removals: {duplicate_removals}, "
                f"Warnings logged: {len(warnings)}"
            )

            return result

        except CitationError:
            raise
        except Exception as e:
            raise CitationError(f"Unexpected citation engine orchestration failure: {e}") from e
