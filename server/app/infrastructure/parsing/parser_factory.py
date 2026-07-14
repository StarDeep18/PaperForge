"""
Parser Factory.

Strategy pattern for selecting the correct document parser
based on file type. Extensible for new formats.
"""

from pathlib import Path

from app.core.logging import logger
from app.domain.entities.document import DocumentMetadata, DocumentType
from app.domain.exceptions import UnsupportedFileTypeError
from app.infrastructure.parsing.pdf_parser import PDFParser
from app.infrastructure.parsing.docx_parser import DOCXParser


class ParseResult:
    """Unified parse result across all document types."""

    def __init__(
        self,
        text: str,
        metadata: DocumentMetadata,
        page_breaks: dict[int, int] | None = None,
    ):
        self.text = text
        self.metadata = metadata
        self.page_breaks = page_breaks or {}


class ParserFactory:
    """
    Factory for creating the appropriate document parser.

    Uses the Strategy pattern — each file type has its own parser
    implementation. New formats are added by creating a new parser
    class and registering it here.
    """

    def __init__(self):
        self._pdf_parser = PDFParser()
        self._docx_parser = DOCXParser()

    def parse(self, file_path: str, file_type: DocumentType) -> ParseResult:
        """
        Parse a document using the appropriate parser.

        Args:
            file_path: Path to the file.
            file_type: The document type (PDF, DOCX, TXT).

        Returns:
            Unified ParseResult.
        """
        logger.info(f"Parsing {file_type.value} file: {file_path}")

        if file_type == DocumentType.PDF:
            result = self._pdf_parser.parse(file_path)
            return ParseResult(
                text=result.text,
                metadata=result.metadata,
                page_breaks=result.page_breaks,
            )

        elif file_type == DocumentType.DOCX:
            result = self._docx_parser.parse(file_path)
            return ParseResult(
                text=result.text,
                metadata=result.metadata,
            )

        elif file_type == DocumentType.TXT:
            return self._parse_txt(file_path)

        else:
            raise UnsupportedFileTypeError(
                file_type.value,
                [t.value for t in DocumentType],
            )

    def _parse_txt(self, file_path: str) -> ParseResult:
        """Simple text file parser."""
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="replace")

        metadata = DocumentMetadata(
            word_count=len(text.split()),
            page_count=1,
        )

        return ParseResult(text=text, metadata=metadata)
