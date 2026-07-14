"""
Upload Document Use Case.

Handles the complete document upload workflow:
1. Validate file type and size
2. Store file on disk
3. Create document record in database
4. Trigger async processing (parse → chunk → embed)
"""

import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import get_current_user_id
from app.domain.entities.document import Document, DocumentStatus, DocumentType
from app.domain.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.storage.local_file_storage import LocalFileStorage


class UploadDocumentUseCase:
    """
    Orchestrates the document upload process.

    Validates, stores, and creates the document record.
    Processing (parsing, chunking, embedding) is handled separately.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        file_storage: LocalFileStorage,
    ):
        self._document_repo = document_repo
        self._file_storage = file_storage
        self._settings = get_settings()

    async def execute(
        self,
        filename: str,
        content: bytes,
        user_id: str,
        collection_id: str | None = None,
    ) -> Document:
        """
        Upload and register a new document.

        Args:
            filename: Original filename from the upload.
            content: Raw file bytes.
            user_id: The uploading user's ID.
            collection_id: Optional collection to assign the document to.

        Returns:
            The created Document entity.

        Raises:
            UnsupportedFileTypeError: If the file extension is not allowed.
            FileTooLargeError: If the file exceeds the size limit.
        """
        # Validate file type
        ext = Path(filename).suffix.lower()
        if ext not in self._settings.allowed_extension_list:
            raise UnsupportedFileTypeError(ext, self._settings.allowed_extension_list)

        # Validate file size
        if len(content) > self._settings.max_upload_size_bytes:
            raise FileTooLargeError(len(content), self._settings.max_upload_size_bytes)

        # Determine document type
        file_type = self._get_document_type(ext)

        # Store file
        stored_filename, file_path = await self._file_storage.save_file(
            content=content,
            original_filename=filename,
            user_id=user_id,
        )

        # Create document entity
        document = Document(
            user_id=user_id,
            filename=stored_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file_type,
            status=DocumentStatus.UPLOADED,
            collection_id=collection_id,
        )

        # Persist to database
        await self._document_repo.create(document)

        logger.info(
            f"Document uploaded: id={document.id}, "
            f"name={filename}, size={len(content)} bytes"
        )

        return document

    def _get_document_type(self, extension: str) -> DocumentType:
        """Map file extension to DocumentType enum."""
        mapping = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".txt": DocumentType.TXT,
        }
        return mapping.get(extension, DocumentType.TXT)
