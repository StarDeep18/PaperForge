"""
PDF Parser using PyMuPDF.

Extracts text, metadata, and structural information from PDF files.
Optimized for academic research papers.
"""

from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from app.core.logging import logger
from app.domain.entities.document import DocumentMetadata
from app.domain.exceptions import DocumentProcessingError


class PDFParseResult:
    """Result of parsing a PDF document."""

    def __init__(
        self,
        text: str,
        metadata: DocumentMetadata,
        page_breaks: dict[int, int],
    ):
        self.text = text
        self.metadata = metadata
        self.page_breaks = page_breaks  # char_offset -> page_number


class PDFParser:
    """
    Extracts text and metadata from PDF files using PyMuPDF.

    Handles:
    - Full text extraction with page tracking
    - Metadata extraction (title, authors, dates, etc.)
    - Page break tracking for citation page numbers
    - Word count estimation
    """

    def parse(self, file_path: str) -> PDFParseResult:
        """
        Parse a PDF file and extract text + metadata.

        Args:
            file_path: Path to the PDF file.

        Returns:
            PDFParseResult with text, metadata, and page breaks.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentProcessingError("", f"File not found: {file_path}")

        try:
            doc = fitz.open(str(path))
        except Exception as e:
            raise DocumentProcessingError("", f"Failed to open PDF: {e}") from e

        try:
            # Extract text with page tracking
            text_parts: list[str] = []
            page_breaks: dict[int, int] = {}
            current_offset = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text("text")

                page_breaks[current_offset] = page_num + 1  # 1-indexed
                text_parts.append(page_text)
                current_offset += len(page_text) + 1  # +1 for newline separator

            full_text = "\n".join(text_parts)

            # Extract metadata
            pdf_metadata = doc.metadata or {}
            metadata = DocumentMetadata(
                title=self._clean_metadata_field(pdf_metadata.get("title")),
                authors=self._parse_authors(pdf_metadata.get("author")),
                publication_date=self._clean_metadata_field(pdf_metadata.get("creationDate")),
                keywords=self._parse_keywords(pdf_metadata.get("keywords")),
                page_count=len(doc),
                word_count=len(full_text.split()),
            )

            # Try to extract abstract from text if not in metadata
            if not metadata.abstract:
                metadata.abstract = self._extract_abstract(full_text)

            # Try to extract title from text if not in metadata
            if not metadata.title:
                metadata.title = self._extract_title_from_text(doc)

            logger.info(
                f"Parsed PDF: {path.name}, "
                f"pages={metadata.page_count}, "
                f"words={metadata.word_count}"
            )

            return PDFParseResult(
                text=full_text,
                metadata=metadata,
                page_breaks=page_breaks,
            )
        finally:
            doc.close()

    def _clean_metadata_field(self, value: Optional[str]) -> Optional[str]:
        """Clean a metadata field value."""
        if not value or not value.strip():
            return None
        # Remove PDF date format prefix if present
        cleaned = value.strip()
        if cleaned.startswith("D:"):
            cleaned = cleaned[2:]
        return cleaned if cleaned else None

    def _parse_authors(self, author_str: Optional[str]) -> list[str]:
        """Parse author string into a list of names."""
        if not author_str or not author_str.strip():
            return []

        # Try common separators
        for sep in [";", " and ", ",", "&"]:
            if sep in author_str:
                return [a.strip() for a in author_str.split(sep) if a.strip()]

        return [author_str.strip()] if author_str.strip() else []

    def _parse_keywords(self, keywords_str: Optional[str]) -> list[str]:
        """Parse keywords string into a list."""
        if not keywords_str or not keywords_str.strip():
            return []

        for sep in [";", ","]:
            if sep in keywords_str:
                return [k.strip() for k in keywords_str.split(sep) if k.strip()]

        return [keywords_str.strip()]

    def _extract_abstract(self, text: str) -> Optional[str]:
        """
        Attempt to extract the abstract from paper text.

        Looks for common patterns in academic papers.
        """
        text_lower = text.lower()

        # Find "abstract" header
        abstract_start = -1
        for marker in ["abstract\n", "abstract\r\n", "abstract ", "abstract."]:
            pos = text_lower.find(marker)
            if pos != -1:
                abstract_start = pos + len(marker)
                break

        if abstract_start == -1:
            return None

        # Find the end of abstract (next section header or double newline)
        remaining = text[abstract_start:]
        end_markers = [
            "\n1.", "\n1 ", "\nintroduction", "\nINTRODUCTION",
            "\nI.", "\nI ", "\nKeywords", "\nkeywords",
        ]

        abstract_end = len(remaining)
        for marker in end_markers:
            pos = remaining.lower().find(marker.lower())
            if pos != -1 and pos < abstract_end:
                abstract_end = pos

        # Also limit by double newlines (but not too aggressively)
        double_newline_pos = remaining.find("\n\n")
        if double_newline_pos != -1 and double_newline_pos > 100:
            # Only use double newline if abstract is reasonably long
            abstract_end = min(abstract_end, double_newline_pos)

        abstract = remaining[:abstract_end].strip()
        return abstract if len(abstract) > 50 else None

    def _extract_title_from_text(self, doc: fitz.Document) -> Optional[str]:
        """
        Extract title from the first page using font size heuristics.

        The title is typically the largest text on the first page.
        """
        if len(doc) == 0:
            return None

        page = doc[0]
        blocks = page.get_text("dict")["blocks"]

        max_size = 0
        title_spans = []

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if text and size > max_size:
                        max_size = size
                        title_spans = [text]
                    elif text and size == max_size:
                        title_spans.append(text)

        if title_spans:
            title = " ".join(title_spans)
            # Sanity check: title shouldn't be too long or too short
            if 5 < len(title) < 300:
                return title

        return None
