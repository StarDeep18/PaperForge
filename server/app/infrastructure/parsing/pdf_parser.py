"""
PDF Parser using PyMuPDF.

Extracts text, metadata, and structural information from PDF files.
Optimized for academic research papers.
"""

from pathlib import Path
import re
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

        # Handle encrypted PDFs
        if doc.is_encrypted:
            success = False
            try:
                # authenticate returns > 0 on success, 0 on failure
                success = doc.authenticate("") > 0
            except Exception as e:
                doc.close()
                raise DocumentProcessingError("", f"Failed to authenticate encrypted PDF: {e}") from e

            if not success:
                doc.close()
                raise DocumentProcessingError("", "PDF is encrypted and requires a password")

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
                publication_date=self._parse_pdf_date(pdf_metadata.get("creationDate")),
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

    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse a PDF date string (often starting with 'D:') into ISO format 'YYYY-MM-DD'.
        """
        if not date_str or not date_str.strip():
            return None

        cleaned = date_str.strip()
        if cleaned.startswith("D:"):
            cleaned = cleaned[2:]

        # If it's already formatted (starts with YYYY-MM or YYYY/MM), return it as is
        if re.match(r"^\d{4}[-/]\d{2}", cleaned):
            return cleaned

        # Match starting digits: YYYYMMDD
        match = re.match(r"^(\d{4})(\d{2})?(\d{2})?", cleaned)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)

            parts = [year]
            if month and int(month) in range(1, 13):
                parts.append(month)
                if day and int(day) in range(1, 32):
                    parts.append(day)
            return "-".join(parts)

        return cleaned if len(cleaned) > 0 else None

    def _parse_authors(self, author_str: Optional[str]) -> list[str]:
        """Parse author string into a list of names."""
        if not author_str or not author_str.strip():
            return []

        # Semicolon is the most reliable separator for multiple authors (e.g. "Doe, John; Smith, Jane")
        if ";" in author_str:
            return [a.strip() for a in author_str.split(";") if a.strip()]

        # Check for 'and' and '&'
        for sep in [" and ", " & "]:
            if sep in author_str:
                return [a.strip() for a in author_str.split(sep) if a.strip()]

        # Comma-separated parsing with heuristics for Last, First format
        if "," in author_str:
            parts = [p.strip() for p in author_str.split(",") if p.strip()]

            # Heuristic for "Last, First" pair format:
            # e.g., "Doe, John, Smith, Jane" -> 4 parts, all single words.
            # If all parts are single words and we have an even number of parts,
            # we combine them into pairs: "John Doe", "Jane Smith".
            is_last_first_format = (
                len(parts) > 0
                and len(parts) % 2 == 0
                and all(" " not in part for part in parts)
            )

            if is_last_first_format:
                combined_authors = []
                for i in range(0, len(parts), 2):
                    last = parts[i]
                    first = parts[i+1]
                    combined_authors.append(f"{first} {last}")
                return combined_authors
            else:
                return parts

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
        # Search for "Abstract" as a section header at the beginning of a line or paragraph
        pattern = r"(?:^|\n)\s*\babstract\b[\s.:]*"
        
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None

        abstract_start = match.end()

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
            abstract_end = min(abstract_end, double_newline_pos)

        abstract = remaining[:abstract_end].strip()
        return abstract if len(abstract) > 50 else None

    def _extract_title_from_text(self, doc: fitz.Document) -> Optional[str]:
        """
        Extract title from the first page using font size heuristics.

        The title is typically the largest text on the first page, located
        in the top 50% of the page.
        """
        if len(doc) == 0:
            return None

        page = doc[0]
        page_height = page.rect.height

        try:
            blocks = page.get_text("dict")["blocks"]
        except Exception:
            return None

        max_size = 0
        title_spans = []

        for block in blocks:
            # Restrict search to blocks in the top 50% of the first page
            if "bbox" not in block or block["bbox"][3] > page_height * 0.5:
                continue

            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()

                    if not text:
                        continue

                    if size > max_size:
                        max_size = size
                        title_spans = [text]
                    elif size == max_size:
                        title_spans.append(text)

        if title_spans:
            title = " ".join(title_spans)
            title = re.sub(r"\s+", " ", title).strip()
            # Sanity check: title shouldn't be too long or too short
            if 5 < len(title) < 300:
                return title

        return None
