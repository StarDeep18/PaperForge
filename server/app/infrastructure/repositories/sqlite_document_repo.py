"""
SQLite Document Repository.

Concrete implementation of DocumentRepository using SQLAlchemy.
Maps between domain Document entities and DocumentModel ORM objects.
"""

from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document, DocumentMetadata, DocumentStatus, DocumentType
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.database.models import DocumentModel


class SQLiteDocumentRepository(DocumentRepository):
    """SQLAlchemy-based document repository implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, document: Document) -> Document:
        model = self._to_model(document)
        self._session.add(model)
        await self._session.flush()
        return document

    async def get_by_id(self, document_id: str, user_id: str) -> Optional[Document]:
        stmt = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        stmt = select(DocumentModel).where(DocumentModel.user_id == user_id)

        if collection_id is not None:
            stmt = stmt.where(DocumentModel.collection_id == collection_id)

        stmt = stmt.order_by(DocumentModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update(self, document: Document) -> Document:
        stmt = select(DocumentModel).where(DocumentModel.id == document.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.filename = document.filename
            model.original_filename = document.original_filename
            model.file_path = document.file_path
            model.file_size = document.file_size
            model.file_type = document.file_type
            model.status = document.status
            model.collection_id = document.collection_id
            model.title = document.metadata.title if document.metadata else None
            model.authors = document.metadata.authors if document.metadata else None
            model.abstract = document.metadata.abstract if document.metadata else None
            model.publication_date = document.metadata.publication_date if document.metadata else None
            model.journal = document.metadata.journal if document.metadata else None
            model.doi = document.metadata.doi if document.metadata else None
            model.keywords = document.metadata.keywords if document.metadata else None
            model.page_count = document.metadata.page_count if document.metadata else 0
            model.word_count = document.metadata.word_count if document.metadata else 0
            model.raw_text = document.raw_text
            model.chunk_count = document.chunk_count
            model.error_message = document.error_message
            model.updated_at = document.updated_at
            await self._session.flush()

        return document

    async def delete(self, document_id: str, user_id: str) -> bool:
        stmt = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def count(self, user_id: str, collection_id: Optional[str] = None) -> int:
        stmt = select(func.count(DocumentModel.id)).where(
            DocumentModel.user_id == user_id
        )
        if collection_id:
            stmt = stmt.where(DocumentModel.collection_id == collection_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_by_ids(self, document_ids: list[str], user_id: str) -> list[Document]:
        stmt = select(DocumentModel).where(
            DocumentModel.id.in_(document_ids),
            DocumentModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    # ── Mapping ──────────────────────────────────────────────────

    def _to_model(self, entity: Document) -> DocumentModel:
        """Map domain entity to ORM model."""
        return DocumentModel(
            id=entity.id,
            user_id=entity.user_id,
            collection_id=entity.collection_id,
            filename=entity.filename,
            original_filename=entity.original_filename,
            file_path=entity.file_path,
            file_size=entity.file_size,
            file_type=entity.file_type,
            status=entity.status,
            title=entity.metadata.title if entity.metadata else None,
            authors=entity.metadata.authors if entity.metadata else None,
            abstract=entity.metadata.abstract if entity.metadata else None,
            publication_date=entity.metadata.publication_date if entity.metadata else None,
            journal=entity.metadata.journal if entity.metadata else None,
            doi=entity.metadata.doi if entity.metadata else None,
            keywords=entity.metadata.keywords if entity.metadata else None,
            page_count=entity.metadata.page_count if entity.metadata else 0,
            word_count=entity.metadata.word_count if entity.metadata else 0,
            raw_text=entity.raw_text,
            chunk_count=entity.chunk_count,
            error_message=entity.error_message,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_entity(self, model: DocumentModel) -> Document:
        """Map ORM model to domain entity."""
        metadata = DocumentMetadata(
            title=model.title,
            authors=model.authors or [],
            abstract=model.abstract,
            publication_date=model.publication_date,
            journal=model.journal,
            doi=model.doi,
            keywords=model.keywords or [],
            page_count=model.page_count or 0,
            word_count=model.word_count or 0,
        )

        return Document(
            id=model.id,
            user_id=model.user_id,
            filename=model.filename,
            original_filename=model.original_filename,
            file_path=model.file_path,
            file_size=model.file_size,
            file_type=model.file_type,
            status=model.status,
            metadata=metadata,
            collection_id=model.collection_id,
            raw_text=model.raw_text,
            chunk_count=model.chunk_count,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
