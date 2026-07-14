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


class EmbeddingProviderUnavailable(EmbeddingError):
    """Raised when the embedding provider is unreachable or down."""

    def __init__(self, provider: str, detail: str):
        super().__init__(f"Provider '{provider}' is unavailable: {detail}")
        self.provider = provider
        self.detail = detail


class EmbeddingDimensionMismatch(EmbeddingError):
    """Raised when the returned embedding dimension does not match expectations."""

    def __init__(self, expected: int, actual: int):
        super().__init__(f"Embedding dimension mismatch: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class EmbeddingTimeout(EmbeddingError):
    """Raised when the embedding request times out."""

    def __init__(self, provider: str, timeout_seconds: float):
        super().__init__(f"Embedding request to '{provider}' timed out after {timeout_seconds}s")
        self.provider = provider
        self.timeout_seconds = timeout_seconds


class InvalidEmbeddingResponse(EmbeddingError):
    """Raised when the response from the embedding API is malformed or empty."""

    def __init__(self, provider: str, detail: str):
        super().__init__(f"Invalid response from provider '{provider}': {detail}")
        self.provider = provider
        self.detail = detail



class LLMError(PaperForgeError):
    """Raised when the LLM call fails."""

    def __init__(self, detail: str):
        super().__init__(f"LLM error: {detail}")


class RetrievalError(PaperForgeError):
    """Raised when vector search fails."""

    def __init__(self, detail: str):
        super().__init__(f"Retrieval error: {detail}")


# ── Vector Store Errors ──────────────────────────────────────────


class VectorStoreError(PaperForgeError):
    """Base exception for all vector store errors."""
    pass


class CollectionNotFound(VectorStoreError):
    """Raised when a collection is not found in the vector store."""

    def __init__(self, collection_name: str):
        super().__init__(f"Collection not found: '{collection_name}'")
        self.collection_name = collection_name


class DuplicateChunk(VectorStoreError):
    """Raised when trying to insert a chunk with a duplicate ID."""

    def __init__(self, chunk_id: str):
        super().__init__(f"Duplicate chunk ID detected: {chunk_id}")
        self.chunk_id = chunk_id


class VectorInsertError(VectorStoreError):
    """Raised when insertion of vectors fails."""

    def __init__(self, detail: str):
        super().__init__(f"Failed to insert vectors: {detail}")
        self.detail = detail


class VectorSearchError(VectorStoreError):
    """Raised when vector similarity search fails."""

    def __init__(self, detail: str):
        super().__init__(f"Failed to search vectors: {detail}")
        self.detail = detail


class VectorDeleteError(VectorStoreError):
    """Raised when deletion of vectors fails."""

    def __init__(self, detail: str):
        super().__init__(f"Failed to delete vectors: {detail}")
        self.detail = detail


class ConnectionFailure(VectorStoreError):
    """Raised when connection to the vector store fails."""

    def __init__(self, provider: str, detail: str):
        super().__init__(f"Failed to connect to vector store provider '{provider}': {detail}")
        self.provider = provider
        self.detail = detail



# ── Chunking Errors ──────────────────────────────────────────────


class ChunkingError(PaperForgeError):
    """Base exception for all chunking-related errors."""
    pass


class EmptyDocumentError(ChunkingError):
    """Raised when the document text to chunk is empty or whitespace."""

    def __init__(self, document_id: str):
        super().__init__(
            f"Failed to chunk document '{document_id}': The document contains no readable text "
            "or is composed entirely of whitespace. Please verify that document parsing succeeded."
        )


class DocumentTooSmallError(ChunkingError):
    """Raised when the document text is too small to be chunked."""

    def __init__(self, document_id: str, text_len: int, min_len: int):
        super().__init__(
            f"Failed to chunk document '{document_id}': The text content is too small to split "
            f"({text_len} characters; requires at least {min_len} characters)."
        )


class MalformedParserOutputError(ChunkingError):
    """Raised when the parser output is malformed (e.g., offsets out of bounds)."""

    def __init__(self, document_id: str, detail: str):
        super().__init__(
            f"Failed to chunk document '{document_id}': The parser returned invalid structure or page breaks. "
            f"Details: {detail}"
        )


class UnsupportedEncodingError(ChunkingError):
    """Raised when the document text contains unsupported encoding or characters."""

    def __init__(self, document_id: str, detail: str):
        super().__init__(
            f"Failed to chunk document '{document_id}': The text content could not be serialized "
            f"due to encoding issues. Details: {detail}"
        )
