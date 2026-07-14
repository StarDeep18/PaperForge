"""
Process Document Use Case.

Handles the full document processing pipeline:
1. Parse document (extract text + metadata)
2. Chunk text into hierarchical parent-child chunks
3. Generate embeddings for each chunk
4. Store embeddings in the vector database
5. Update document status to READY

This is the heavy-lifting use case triggered after upload.
"""

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.entities.document import Document
from app.domain.exceptions import DocumentProcessingError
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.vector_store import VectorStore
from app.domain.services.chunking_service import ChunkingConfig, ChunkingService
from app.infrastructure.ai.embedding_provider import EmbeddingProvider
from app.infrastructure.parsing.parser_factory import ParserFactory


class ProcessDocumentUseCase:
    """
    Orchestrates the full document processing pipeline.

    Takes a newly uploaded document through:
    UPLOADED → PARSING → PARSED → CHUNKING → EMBEDDING → READY

    Each step updates the document status so the frontend
    can show progress to the user.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        parser_factory: ParserFactory,
    ):
        self._document_repo = document_repo
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._parser_factory = parser_factory

        settings = get_settings()
        self._chunking_service = ChunkingService(
            config=ChunkingConfig(
                child_chunk_size=settings.chunk_size,
                child_chunk_overlap=settings.chunk_overlap,
                parent_chunk_size=settings.parent_chunk_size,
                parent_chunk_overlap=settings.parent_chunk_overlap,
            )
        )

    async def execute(self, document: Document) -> Document:
        """
        Process a document through the full pipeline.

        Args:
            document: The document to process (status should be UPLOADED).

        Returns:
            The updated document with READY status.

        Raises:
            DocumentProcessingError: If any step fails.
        """
        try:
            # ── Step 1: Parse ────────────────────────────────────
            document.mark_parsing()
            await self._document_repo.update(document)

            logger.info(f"Parsing document: {document.id}")
            parse_result = self._parser_factory.parse(
                file_path=document.file_path,
                file_type=document.file_type,
            )

            document.mark_parsed(
                raw_text=parse_result.text,
                metadata=parse_result.metadata,
            )
            await self._document_repo.update(document)

            # ── Step 2: Chunk ────────────────────────────────────
            document.mark_chunking()
            await self._document_repo.update(document)

            logger.info(f"Chunking document: {document.id}")
            chunk_result = self._chunking_service.chunk_document(
                document_id=document.id,
                text=parse_result.text,
                page_breaks=parse_result.page_breaks,
            )
            chunks = chunk_result.payload

            if not chunks:
                raise DocumentProcessingError(
                    document.id,
                    "No text chunks extracted from document",
                )

            # Add document metadata to each chunk for retrieval context
            for chunk in chunks:
                chunk.metadata["document_title"] = document.display_title

            logger.info(f"Created {len(chunks)} chunks for document {document.id}")

            # ── Step 3: Embed ────────────────────────────────────
            document.mark_embedding()
            await self._document_repo.update(document)

            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.content for chunk in chunks]

            # Batch embeddings (avoid overloading API)
            batch_size = 50
            all_embeddings: list[list[float]] = []

            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i : i + batch_size]
                batch_embeddings = await self._embedding_provider.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)

            # Assign embeddings to chunks
            for chunk, embedding in zip(chunks, all_embeddings):
                chunk.embedding = embedding

            # ── Step 4: Store in Vector DB ───────────────────────
            logger.info(f"Storing {len(chunks)} chunks in vector database")
            await self._vector_store.add_chunks(chunks)

            # ── Step 5: Mark Ready ───────────────────────────────
            document.mark_ready(chunk_count=len(chunks))
            await self._document_repo.update(document)

            logger.info(
                f"Document processed successfully: id={document.id}, "
                f"chunks={len(chunks)}, title={document.display_title}"
            )

            return document

        except DocumentProcessingError:
            raise
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(f"Document {document.id}: {error_msg}")
            document.mark_failed(error_msg)
            await self._document_repo.update(document)
            raise DocumentProcessingError(document.id, str(e)) from e
