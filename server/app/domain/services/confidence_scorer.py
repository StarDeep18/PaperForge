"""
Confidence Scorer.

Offline scorer evaluating evidence grounding confidence based on similarity metrics,
evidence density, document diversity, and consistency variance.
"""

import math
from typing import Optional
from app.core.config import get_settings
from app.domain.entities.citation import EvidenceReference
from app.domain.exceptions import ConfidenceScoringError


class ConfidenceScorer:
    """
    Evaluates evidence references offline to compute confidence categories (High/Medium/Low)
    and normalized score diagnostics.
    """

    def calculate_reference_confidence(self, reference: EvidenceReference) -> float:
        """
        Evaluate individual evidence reference score.
        """
        # Individual chunk confidence corresponds to its similarity score
        return max(0.0, min(1.0, reference.similarity_score))

    def score_evidence(
        self,
        references: list[EvidenceReference],
        high_threshold: Optional[float] = None,
        medium_threshold: Optional[float] = None,
    ) -> tuple[str, float]:
        """
        Calculate overall confidence category and normalized score for all references.

        Args:
            references: Mapped evidence references.
            high_threshold: High confidence category boundary override.
            medium_threshold: Medium confidence category boundary override.

        Returns:
            A tuple of (ConfidenceCategory, NormalizedScore) where category is "High", "Medium", or "Low".

        Raises:
            ConfidenceScoringError: If calculations fail.
        """
        if not references:
            return "Low", 0.0

        settings = get_settings()
        th_high = high_threshold or settings.citation_high_confidence_threshold
        th_medium = medium_threshold or settings.citation_medium_confidence_threshold

        try:
            # Update individual confidence scores first
            for ref in references:
                ref.confidence = self.calculate_reference_confidence(ref)

            # ── 1. Mean Similarity score ──────────────────────────────
            mean_similarity = sum(ref.similarity_score for ref in references) / len(references)

            # ── 2. Chunk Volume Multiplier (Evidence density) ─────────
            # More chunks yields higher support, up to a point
            count_multiplier = min(1.0, 0.5 + (len(references) * 0.1))

            # ── 3. Document Diversity ──────────────────────────────────
            # Having evidence spread across multiple unique papers is a bonus
            unique_docs = len(set(ref.document_id for ref in references))
            diversity_factor = min(1.0, 0.8 + (unique_docs * 0.05))

            # ── 4. Evidence Consistency ───────────────────────────────
            # Lower variance in scores indicates consistent evidence
            if len(references) > 1:
                variance = sum((ref.similarity_score - mean_similarity) ** 2 for ref in references) / len(references)
                std_dev = math.sqrt(variance)
                consistency_multiplier = max(0.8, 1.0 - std_dev)
            else:
                consistency_multiplier = 1.0

            # ── 5. Combined Normalized Score ──────────────────────────
            normalized_score = mean_similarity * count_multiplier * diversity_factor * consistency_multiplier
            normalized_score = max(0.0, min(1.0, normalized_score))

            # ── 6. Category Assignment ────────────────────────────────
            if normalized_score >= th_high:
                category = "High"
            elif normalized_score >= th_medium:
                category = "Medium"
            else:
                category = "Low"

            return category, normalized_score

        except Exception as e:
            raise ConfidenceScoringError(f"Failed to calculate confidence score: {e}") from e
