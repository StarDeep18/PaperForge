"""
Chunking Service.

Domain service for splitting document text into chunks
using a hierarchical parent-child strategy.

This is a pure domain service — no framework dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.domain.entities.chunk import Chunk


@dataclass
class ChunkingConfig:
    """Configuration for the chunking pipeline."""

    child_chunk_size: int = 512       # tokens (approx chars / 4)
    child_chunk_overlap: int = 50
    parent_chunk_size: int = 1500
    parent_chunk_overlap: int = 150


class ChunkingService:
    """
    Splits document text into hierarchical parent-child chunks.

    Strategy:
    1. Split into large parent chunks (~1500 tokens)
    2. Split each parent into smaller child chunks (~512 tokens)
    3. Each child chunk stores a reference to its parent content
    4. Child chunks go to the vector DB for precise retrieval
    5. Parent content is passed to the LLM for richer context

    This solves the precision-vs-context trade-off in RAG.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()

    def chunk_document(
        self,
        document_id: str,
        text: str,
        page_breaks: Optional[dict[int, int]] = None,
    ) -> list[Chunk]:
        """
        Split document text into hierarchical chunks.

        Args:
            document_id: The document ID to associate with chunks.
            text: The full text content of the document.
            page_breaks: Optional mapping of character offset → page number.

        Returns:
            List of child Chunk entities with parent content attached.
        """
        if not text or not text.strip():
            return []

        # Step 1: Create parent chunks
        parent_chunks = self._split_text(
            text,
            chunk_size=self.config.parent_chunk_size,
            overlap=self.config.parent_chunk_overlap,
        )

        # Step 2: Split each parent into children
        all_chunks: list[Chunk] = []
        chunk_index = 0

        for parent_text in parent_chunks:
            child_texts = self._split_text(
                parent_text,
                chunk_size=self.config.child_chunk_size,
                overlap=self.config.child_chunk_overlap,
            )

            for child_text in child_texts:
                page_number = None
                if page_breaks:
                    # Find which page this chunk belongs to
                    char_pos = text.find(child_text[:100])
                    if char_pos >= 0:
                        page_number = self._find_page(char_pos, page_breaks)

                section_header = self._detect_section_header(child_text)

                chunk = Chunk(
                    document_id=document_id,
                    content=child_text.strip(),
                    parent_content=parent_text.strip(),
                    page_number=page_number,
                    section_header=section_header,
                    chunk_index=chunk_index,
                    token_count=self._estimate_tokens(child_text),
                )
                all_chunks.append(chunk)
                chunk_index += 1

        return all_chunks

    def _split_text(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """
        Recursive character splitter with sentence-boundary awareness.

        Tries to split at paragraph breaks, then sentences, then words.
        Falls back to character splitting only as a last resort.
        """
        # Convert token size to approximate character count (1 token ≈ 4 chars)
        char_size = chunk_size * 4
        char_overlap = overlap * 4

        if len(text) <= char_size:
            return [text] if text.strip() else []

        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]
        return self._recursive_split(text, separators, char_size, char_overlap)

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
        overlap: int,
    ) -> list[str]:
        """Split text recursively, trying each separator in order."""
        if not separators:
            # Last resort: split by character count
            return self._split_by_size(text, chunk_size, overlap)

        separator = separators[0]
        remaining_separators = separators[1:]

        parts = text.split(separator)
        if len(parts) == 1:
            # This separator doesn't appear; try next
            return self._recursive_split(text, remaining_separators, chunk_size, overlap)

        chunks: list[str] = []
        current_chunk = ""

        for part in parts:
            candidate = (
                current_chunk + separator + part if current_chunk else part
            )

            if len(candidate) <= chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If this part alone exceeds chunk_size, split it further
                if len(part) > chunk_size:
                    sub_chunks = self._recursive_split(
                        part, remaining_separators, chunk_size, overlap
                    )
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap between adjacent chunks
        if overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, overlap)

        return [c for c in chunks if c.strip()]

    def _split_by_size(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """Fallback: split by character count with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap if overlap > 0 else end
        return chunks

    def _add_overlap(self, chunks: list[str], overlap: int) -> list[str]:
        """Add overlapping text between adjacent chunks."""
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
            result.append(prev_tail + chunks[i])
        return result

    def _find_page(self, char_offset: int, page_breaks: dict[int, int]) -> int:
        """Find the page number for a given character offset."""
        page = 1
        for offset, page_num in sorted(page_breaks.items()):
            if char_offset >= offset:
                page = page_num
            else:
                break
        return page

    def _detect_section_header(self, text: str) -> Optional[str]:
        """
        Attempt to detect a section header at the start of a chunk.

        Looks for common academic paper section patterns:
        - "1. Introduction"
        - "Abstract"
        - "METHODS"
        - "3.2 Data Collection"
        """
        lines = text.strip().split("\n")
        if not lines:
            return None

        first_line = lines[0].strip()

        # Match numbered sections: "1.", "1.1", "1.1.1"
        section_pattern = r"^(\d+\.?\d*\.?\d*)\s+(.+)$"
        match = re.match(section_pattern, first_line)
        if match:
            return match.group(2).strip()

        # Match known section headers
        known_sections = [
            "abstract", "introduction", "background", "related work",
            "methodology", "methods", "materials and methods",
            "results", "discussion", "conclusion", "conclusions",
            "references", "bibliography", "acknowledgments",
            "appendix", "supplementary",
        ]
        if first_line.lower().rstrip(":") in known_sections:
            return first_line.strip()

        return None

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimation (1 token ≈ 4 characters)."""
        return len(text) // 4
