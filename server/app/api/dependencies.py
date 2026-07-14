"""
FastAPI Dependency Injection Factories.

Centralizes the creation of all dependencies (repositories, services, use cases)
using FastAPI's Depends() system. This is the composition root of the application.
"""

from typing import Annotated
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.core.config import get_settings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.repositories.sqlite_document_repo import SQLiteDocumentRepository
from app.infrastructure.repositories.sqlite_collection_repo import SQLiteCollectionRepository
from app.infrastructure.repositories.sqlite_conversation_repo import SQLiteConversationRepository
from app.infrastructure.repositories.chroma_vector_store import ChromaVectorStore
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.services.embedding_service import EmbeddingService
from app.domain.services.vector_store_service import VectorStoreService
from app.infrastructure.ai.gemini_embedding_provider import GeminiEmbeddingProvider
from app.infrastructure.ai.mock_embedding_provider import MockEmbeddingProvider
from app.infrastructure.ai.llm_provider import LLMProvider
from app.infrastructure.ai.rag_chain import RAGChain
from app.infrastructure.parsing.parser_factory import ParserFactory
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.application.documents.upload_document import UploadDocumentUseCase
from app.application.documents.process_document import ProcessDocumentUseCase
from app.application.chat.send_message import SendMessageUseCase
from app.domain.services.collection_manager import CollectionManager
from app.domain.services.retrieval_service import RetrievalService
from app.infrastructure.repositories.chroma_vector_store import ChromaCollectionManager



# ── Singletons (created once, reused) ───────────────────────────


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    """Singleton ChromaDB vector store."""
    return ChromaVectorStore()


@lru_cache
def get_vector_store_service() -> VectorStoreService:
    """Singleton vector store service orchestrator."""
    vector_store = get_vector_store()
    return VectorStoreService(vector_store=vector_store)


@lru_cache
def get_collection_manager() -> CollectionManager:
    """Singleton collection manager."""
    return ChromaCollectionManager()




@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Singleton embedding provider based on configuration."""
    settings = get_settings()
    prov = settings.embedding_provider.lower()
    if prov == "gemini":
        return GeminiEmbeddingProvider()
    elif prov == "mock":
        return MockEmbeddingProvider(dimension=settings.embedding_dimension)
    else:
        raise ValueError(f"Unsupported embedding provider: {prov}")


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Singleton embedding orchestrator service."""
    provider = get_embedding_provider()
    return EmbeddingService(provider=provider)


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Singleton retrieval service."""
    embedding_provider = get_embedding_provider()
    vector_store_service = get_vector_store_service()
    return RetrievalService(
        embedding_provider=embedding_provider,
        vector_store_service=vector_store_service,
    )




@lru_cache
def get_llm_provider() -> LLMProvider:
    """Singleton LLM provider."""
    return LLMProvider()


@lru_cache
def get_parser_factory() -> ParserFactory:
    """Singleton parser factory."""
    return ParserFactory()


@lru_cache
def get_file_storage() -> LocalFileStorage:
    """Singleton file storage."""
    return LocalFileStorage()


# ── Type Aliases ─────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]


# ── Repository Factories ────────────────────────────────────────


def get_document_repo(session: DbSession) -> SQLiteDocumentRepository:
    """Per-request document repository."""
    return SQLiteDocumentRepository(session)


def get_collection_repo(session: DbSession) -> SQLiteCollectionRepository:
    """Per-request collection repository."""
    return SQLiteCollectionRepository(session)


def get_conversation_repo(session: DbSession) -> SQLiteConversationRepository:
    """Per-request conversation repository."""
    return SQLiteConversationRepository(session)


# ── Use Case Factories ──────────────────────────────────────────


def get_upload_document_use_case(
    document_repo: Annotated[SQLiteDocumentRepository, Depends(get_document_repo)],
    file_storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
) -> UploadDocumentUseCase:
    """Upload document use case."""
    return UploadDocumentUseCase(
        document_repo=document_repo,
        file_storage=file_storage,
    )


def get_process_document_use_case(
    document_repo: Annotated[SQLiteDocumentRepository, Depends(get_document_repo)],
    vector_store_service: Annotated[VectorStoreService, Depends(get_vector_store_service)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    parser_factory: Annotated[ParserFactory, Depends(get_parser_factory)],
) -> ProcessDocumentUseCase:
    """Process document use case."""
    return ProcessDocumentUseCase(
        document_repo=document_repo,
        vector_store_service=vector_store_service,
        embedding_service=embedding_service,
        parser_factory=parser_factory,
    )




def get_rag_chain(
    vector_store: Annotated[ChromaVectorStore, Depends(get_vector_store)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> RAGChain:
    """RAG chain instance."""
    return RAGChain(
        vector_store=vector_store,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
    )


def get_send_message_use_case(
    conversation_repo: Annotated[SQLiteConversationRepository, Depends(get_conversation_repo)],
    document_repo: Annotated[SQLiteDocumentRepository, Depends(get_document_repo)],
    rag_chain: Annotated[RAGChain, Depends(get_rag_chain)],
) -> SendMessageUseCase:
    """Send message use case."""
    return SendMessageUseCase(
        conversation_repo=conversation_repo,
        document_repo=document_repo,
        rag_chain=rag_chain,
    )
