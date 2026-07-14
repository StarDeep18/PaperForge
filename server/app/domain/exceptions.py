"""
Domain Exceptions.

All domain-specific exceptions live here. These are raised by
domain logic and caught/translated by the presentation layer.
"""


class PaperForgeError(Exception):
    """Base exception for all PaperForge domain errors."""

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)


# ── Document Errors ──────────────────────────────────────────────


class DocumentNotFoundError(PaperForgeError):
    """Raised when a document is not found."""

    def __init__(self, document_id: str):
        super().__init__(f"Document not found: {document_id}")
        self.document_id = document_id


class DocumentAlreadyExistsError(PaperForgeError):
    """Raised when uploading a duplicate document."""

    def __init__(self, filename: str):
        super().__init__(f"Document already exists: {filename}")
        self.filename = filename


class DocumentProcessingError(PaperForgeError):
    """Raised when document parsing or processing fails."""

    def __init__(self, document_id: str, detail: str):
        super().__init__(f"Processing failed for {document_id}: {detail}")
        self.document_id = document_id
        self.detail = detail


class UnsupportedFileTypeError(PaperForgeError):
    """Raised when an unsupported file type is uploaded."""

    def __init__(self, file_type: str, allowed: list[str]):
        super().__init__(
            f"Unsupported file type: {file_type}. Allowed: {', '.join(allowed)}"
        )
        self.file_type = file_type
        self.allowed = allowed


class FileTooLargeError(PaperForgeError):
    """Raised when a file exceeds the maximum upload size."""

    def __init__(self, size_bytes: int, max_bytes: int):
        size_mb = size_bytes / (1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        super().__init__(
            f"File size ({size_mb:.1f}MB) exceeds maximum ({max_mb:.0f}MB)"
        )
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


# ── Collection Errors ────────────────────────────────────────────


class CollectionNotFoundError(PaperForgeError):
    """Raised when a collection is not found."""

    def __init__(self, collection_id: str):
        super().__init__(f"Collection not found: {collection_id}")
        self.collection_id = collection_id


# ── Conversation Errors ─────────────────────────────────────────


class ConversationNotFoundError(PaperForgeError):
    """Raised when a conversation is not found."""

    def __init__(self, conversation_id: str):
        super().__init__(f"Conversation not found: {conversation_id}")
        self.conversation_id = conversation_id


# ── AI / RAG Errors ─────────────────────────────────────────────


class EmbeddingError(PaperForgeError):
    """Raised when embedding generation fails."""

    def __init__(self, detail: str):
        super().__init__(f"Embedding generation failed: {detail}")


class LLMError(PaperForgeError):
    """Raised when the LLM call fails."""

    def __init__(self, detail: str):
        super().__init__(f"LLM error: {detail}")


class RetrievalError(PaperForgeError):
    """Raised when vector search fails."""

    def __init__(self, detail: str):
        super().__init__(f"Retrieval error: {detail}")
