"""
Chunking Service.

Domain service for splitting document text into chunks
using a hierarchical parent-child strategy.

This is a pure domain service — no framework dependencies.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import re
import time
from typing import Optional

from app.core.logging import logger
from app.domain.entities.chunk import Chunk, ProcessingResult
from app.domain.exceptions import (
    EmptyDocumentError,
    DocumentTooSmallError,
    MalformedParserOutputError,
    UnsupportedEncodingError,
)


@dataclass
class ChunkingConfig:
    """
    Configuration parameters for the text chunking process.

    Attributes:
        child_chunk_size (int): Target token size for child retrieval chunks.
        child_chunk_overlap (int): Token overlap size between adjacent child chunks.
        parent_chunk_size (int): Target token size for parent synthesis chunks.
        parent_chunk_overlap (int): Token overlap size between adjacent parent chunks.
    """

    child_chunk_size: int = 512       # tokens (approx chars / 4)
    child_chunk_overlap: int = 50
    parent_chunk_size: int = 1500
    parent_chunk_overlap: int = 150


class ChunkingStrategy(ABC):
    """
    Abstract Base Class defining the contract for document chunking algorithms.
    """

    @abstractmethod
    def chunk_document(
        self,
        document_id: str,
        text: str,
        page_breaks: Optional[dict[int, int]] = None,
    ) -> list[Chunk]:
        """
        Split document text into a list of Chunk domain entities.

        Args:
            document_id (str): The unique identifier of the source document.
            text (str): The full parsed text content.
            page_breaks (Optional[dict[int, int]]): Mapping of absolute char offset to page number.

        Returns:
            list[Chunk]: Generated child Chunk entities with parent references.
        """
        pass


class HierarchicalChunkingStrategy(ChunkingStrategy):
    """
    Concrete strategy implementation for hierarchical parent-child chunking.

    Splits the document into large parent contexts for generation, and smaller child
    segments with overlaps for highly-precise vector retrieval.
    """

    def __init__(self, config: ChunkingConfig):
        """
        Initialize the hierarchical strategy with configuration.

        Args:
            config (ChunkingConfig): Chunk sizes and overlap settings.
        """
        self.config = config

    def chunk_document(
        self,
        document_id: str,
        text: str,
        page_breaks: Optional[dict[int, int]] = None,
    ) -> list[Chunk]:
        """
        Implement hierarchical parent-child splitting with page coordinate tracking and deterministic IDs.

        Args:
            document_id (str): Document identifier.
            text (str): Parsed string text.
            page_breaks (Optional[dict[int, int]]): Page offset metadata.

        Returns:
            list[Chunk]: List of children with parent links and page-relative offsets.
        """
        # Step 1: Create parent chunks
        parent_chunks = self._split_text(
            text,
            chunk_size=self.config.parent_chunk_size,
            overlap=self.config.parent_chunk_overlap,
            base_offset=0,
        )

        # Step 2: Split each parent into children
        all_chunks: list[Chunk] = []
        chunk_index = 0

        for parent_text, parent_offset in parent_chunks:
            # Generate deterministic parent ID
            parent_id_str = f"{document_id}:parent:{parent_offset}"
            parent_chunk_id = hashlib.sha256(parent_id_str.encode("utf-8")).hexdigest()

            child_chunks = self._split_text(
                parent_text,
                chunk_size=self.config.child_chunk_size,
                overlap=self.config.child_chunk_overlap,
                base_offset=parent_offset,
            )

            for child_text, child_offset in child_chunks:
                page_number = 1
                page_relative_start = child_offset
                page_relative_end = child_offset + len(child_text)

                if page_breaks:
                    page_start_offset = 0
                    for offset, p_num in sorted(page_breaks.items()):
                        if child_offset >= offset:
                            page_number = p_num
                            page_start_offset = offset
                        else:
                            break
                    page_relative_start = child_offset - page_start_offset
                    page_relative_end = (child_offset + len(child_text)) - page_start_offset

                section_header = self._detect_section_header(child_text)

                # Generate stable deterministic child ID
                id_str = f"{document_id}:{chunk_index}:{child_text.strip()}"
                chunk_id = hashlib.sha256(id_str.encode("utf-8")).hexdigest()

                chunk = Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    content=child_text.strip(),
                    parent_content=parent_text.strip(),
                    parent_chunk_id=parent_chunk_id,
                    page_number=page_number,
                    section_header=section_header,
                    chunk_index=chunk_index,
                    token_count=self._estimate_tokens(child_text),
                    character_start=child_offset,
                    character_end=child_offset + len(child_text),
                    page_relative_start=page_relative_start,
                    page_relative_end=page_relative_end,
                )
                all_chunks.append(chunk)
                chunk_index += 1

        total_chunks = len(all_chunks)
        for chunk in all_chunks:
            chunk.total_chunks = total_chunks

        return all_chunks

    def _split_text(
        self, text: str, chunk_size: int, overlap: int, base_offset: int = 0
    ) -> list[tuple[str, int]]:
        """Split text using recursive separators."""
        char_size = chunk_size * 4
        char_overlap = overlap * 4

        if len(text) <= char_size:
            return [(text, base_offset)] if text.strip() else []

        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]
        chunks = self._recursive_split(text, separators, char_size, char_overlap, base_offset)

        if char_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, text, char_overlap, base_offset)

        return [(t, off) for t, off in chunks if t.strip()]

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
        overlap: int,
        base_offset: int,
    ) -> list[tuple[str, int]]:
        """Split text recursively, trying each separator in order."""
        if not separators:
            return self._split_by_size(text, chunk_size, overlap, base_offset)

        separator = separators[0]
        remaining_separators = separators[1:]

        parts = text.split(separator)
        if len(parts) == 1:
            return self._recursive_split(text, remaining_separators, chunk_size, overlap, base_offset)

        chunks: list[tuple[str, int]] = []
        current_chunk_parts: list[str] = []
        current_chunk_len = 0
        current_start_offset = base_offset

        current_offset = base_offset
        for part in parts:
            part_len = len(part)

            candidate_len = current_chunk_len + (len(separator) if current_chunk_len > 0 else 0) + part_len

            if candidate_len <= chunk_size:
                current_chunk_parts.append(part)
                current_chunk_len = candidate_len
            else:
                if current_chunk_parts:
                    chunk_text = separator.join(current_chunk_parts)
                    chunks.append((chunk_text, current_start_offset))

                if part_len > chunk_size:
                    sub_chunks = self._recursive_split(
                        part, remaining_separators, chunk_size, overlap, current_offset
                    )
                    chunks.extend(sub_chunks)
                    current_chunk_parts = []
                    current_chunk_len = 0
                    current_start_offset = current_offset + part_len + len(separator)
                else:
                    current_chunk_parts = [part]
                    current_chunk_len = part_len
                    current_start_offset = current_offset

            current_offset += part_len + len(separator)

        if current_chunk_parts:
            chunk_text = separator.join(current_chunk_parts)
            chunks.append((chunk_text, current_start_offset))

        return [(t, off) for t, off in chunks if t.strip()]

    def _split_by_size(
        self, text: str, chunk_size: int, overlap: int, base_offset: int
    ) -> list[tuple[str, int]]:
        """Fallback splitting text by exact character size bounds."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append((chunk_text, base_offset + start))
            if end >= len(text):
                break
            start = end - overlap if overlap > 0 else end
        return chunks

    def _add_overlap(
        self, chunks: list[tuple[str, int]], text: str, overlap: int, base_offset: int
    ) -> list[tuple[str, int]]:
        """Inject overlaps by direct character offsets slicing."""
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            curr_text, curr_offset = chunks[i]
            rel_curr_offset = curr_offset - base_offset
            rel_new_start = max(0, rel_curr_offset - overlap)
            rel_end = rel_curr_offset + len(curr_text)
            new_text = text[rel_new_start:rel_end]
            new_offset = base_offset + rel_new_start
            result.append((new_text, new_offset))
        return result

    def _find_page(self, char_offset: int, page_breaks: dict[int, int]) -> int:
        """Locate current page number by character offset."""
        page = 1
        for offset, page_num in sorted(page_breaks.items()):
            if char_offset >= offset:
                page = page_num
            else:
                break
        return page

    def _detect_section_header(self, text: str) -> Optional[str]:
        """Detect academic sections starting a text chunk."""
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
        """Estimate token length using character ratios."""
        return len(text) // 4


class ChunkingService:
    """
    Orchestrator service executing document chunking using a ChunkingStrategy.
    """

    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        strategy: Optional[ChunkingStrategy] = None,
    ):
        """
        Initialize the ChunkingService.

        Args:
            config (Optional[ChunkingConfig]): Chunking settings.
            strategy (Optional[ChunkingStrategy]): Concrete chunking strategy to use.
        """
        self.config = config or ChunkingConfig()
        self.strategy = strategy or HierarchicalChunkingStrategy(self.config)

    def chunk_document(
        self,
        document_id: str,
        text: str,
        page_breaks: Optional[dict[int, int]] = None,
    ) -> ProcessingResult:
        """
        Validate document input, run the chunking strategy, gather statistics, and return a result.

        Args:
            document_id (str): The unique identifier of the document.
            text (str): Fully extracted document text.
            page_breaks (Optional[dict[int, int]]): Page boundary mappings.

        Returns:
            ProcessingResult: The standardized result wrapper.

        Raises:
            EmptyDocumentError: If text is empty or whitespaces only.
            UnsupportedEncodingError: If text fails standard encoding formats.
            MalformedParserOutputError: If page breaks have invalid coordinates.
        """
        start_time = time.perf_counter()

        # Run input validations
        self._validate_input(document_id, text, page_breaks)

        warnings = []
        # Check size threshold warning (e.g. over 1MB of text)
        if len(text) > 1000000:
            warnings.append("Document size is unusually large; performance may be impacted.")

        # Chunk the text using the strategy
        chunks = self.strategy.chunk_document(document_id, text, page_breaks)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Calculate statistics
        total_chunks = len(chunks)
        total_chars = len(text)
        avg_chunk_size = sum(len(c.content) for c in chunks) / total_chunks if total_chunks > 0 else 0.0
        overlap_size = self.config.child_chunk_overlap * 4

        statistics = {
            "total_chunks": total_chunks,
            "average_chunk_size": avg_chunk_size,
            "overlap_size": overlap_size,
            "total_characters": total_chars,
            "processing_duration_ms": duration_ms,
        }

        # Log completion using standard logger structure
        page_count = len(page_breaks) if page_breaks else 1
        logger.info(
            f"Chunking completed: doc_id='{document_id}', "
            f"pages={page_count}, characters={total_chars}, "
            f"chunks_generated={total_chunks}, avg_chunk_size={avg_chunk_size:.1f} chars, "
            f"duration={duration_ms:.1f}ms"
        )

        return ProcessingResult(
            success=True,
            duration_ms=duration_ms,
            warnings=warnings,
            statistics=statistics,
            payload=chunks,
        )

    def _validate_input(
        self,
        document_id: str,
        text: str,
        page_breaks: Optional[dict[int, int]] = None,
    ) -> None:
        """
        Perform standard validations on document inputs.

        Args:
            document_id (str): Document ID.
            text (str): Extracted text.
            page_breaks (Optional[dict[int, int]]): Page mapping ranges.
        """
        if not text or not text.strip():
            raise EmptyDocumentError(document_id)

        try:
            text.encode("utf-8").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            raise UnsupportedEncodingError(document_id, str(e))

        if page_breaks:
            for offset, page_num in page_breaks.items():
                if offset < 0 or offset > len(text):
                    raise MalformedParserOutputError(
                        document_id,
                        f"Page break offset {offset} is out of bounds for text of length {len(text)}"
                    )
                if page_num <= 0:
                    raise MalformedParserOutputError(
                        document_id,
                        f"Invalid page number {page_num} in page breaks"
                    )
