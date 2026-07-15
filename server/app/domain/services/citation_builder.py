"""
Citation Builder.

Groups mapped evidence references by document, consolidates consecutive page ranges,
removes duplicate records, and formats structured citations.
"""

from typing import Optional
from app.core.config import get_settings
from app.domain.entities.citation import Citation, EvidenceReference
from app.domain.exceptions import CitationFormattingError


class CitationBuilder:
    """
    Groups evidence references and builds formatted citations.
    """

    def merge_pages(self, pages: list[int], policy: str = "consecutive") -> str:
        """
        Merge a list of page integers into a ranges string (e.g. [1, 2, 3, 5] -> "1-3, 5").
        """
        # Filter out invalid page entries
        valid_pages = sorted(list(set([p for p in pages if p is not None])))
        if not valid_pages:
            return ""

        if policy != "consecutive" or len(valid_pages) == 1:
            return ", ".join(str(p) for p in valid_pages)

        ranges = []
        start = valid_pages[0]
        prev = start

        for p in valid_pages[1:]:
            if p == prev + 1:
                prev = p
            else:
                if start == prev:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{prev}")
                start = p
                prev = p

        if start == prev:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{prev}")

        return ", ".join(ranges)

    def build_citations(
        self,
        references: list[EvidenceReference],
        grouping_policy: Optional[str] = None,
        page_merge_policy: Optional[str] = None,
    ) -> list[Citation]:
        """
        Group references, deduplicate, and format Citation list.

        Args:
            references: Mapped evidence references.
            grouping_policy: Grouping option ("document" or "page").
            page_merge_policy: Merging policy option ("consecutive" or "none").

        Returns:
            A list of Citation objects.

        Raises:
            CitationFormattingError: If formatting or consolidation fails.
        """
        if not references:
            return []

        settings = get_settings()
        group_by = grouping_policy or settings.citation_grouping
        merge_by = page_merge_policy or settings.citation_page_merge_policy

        try:
            # ── 1. Group references by Document ID ────────────────────
            # To support future formatting strategies, we group by document
            doc_groups = {}
            for ref in references:
                doc_groups.setdefault(ref.document_id, []).append(ref)

            citations = []
            citation_index = 1

            for doc_id, doc_refs in doc_groups.items():
                # Dedup supporting chunk IDs
                supporting_chunk_ids = sorted(list(set(ref.chunk_id for ref in doc_refs)))
                
                # Retrieve unique page numbers
                pages = []
                for ref in doc_refs:
                    if ref.page_number is not None:
                        pages.append(ref.page_number)
                pages = sorted(list(set(pages)))

                # Merge consecutive page ranges
                page_str = self.merge_pages(pages, merge_by)
                
                # Determine title
                doc_title = doc_refs[0].document_title or "Unknown Document"

                # Calculate average confidence
                avg_confidence_val = sum(ref.confidence for ref in doc_refs) / len(doc_refs)
                if avg_confidence_val >= settings.citation_high_confidence_threshold:
                    confidence_cat = "High"
                elif avg_confidence_val >= settings.citation_medium_confidence_threshold:
                    confidence_cat = "Medium"
                else:
                    confidence_cat = "Low"

                # Build default formatting reference
                formatted_ref = doc_title
                if page_str:
                    formatted_ref += f", p. {page_str}"

                citation = Citation(
                    citation_id=f"cit-{citation_index}",
                    document_id=doc_id,
                    document_title=doc_title,
                    pages=pages,
                    supporting_chunks=supporting_chunk_ids,
                    confidence=confidence_cat,
                    formatted_reference=formatted_ref,
                )
                citations.append(citation)
                citation_index += 1

            return citations

        except Exception as e:
            raise CitationFormattingError(f"Failed to build citations from references: {e}") from e
