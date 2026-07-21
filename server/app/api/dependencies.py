"""
FastAPI Dependency Injection Factories.

Centralizes the creation of all dependencies (repositories, services, use cases)
using FastAPI's Depends() system. This is the composition root of the application.
"""

from typing import Annotated, Optional
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.firebase import verify_firebase_token
from app.domain.models.user import User
from app.core.config import get_settings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.repositories.user_repository import SQLiteUserRepository
from app.infrastructure.repositories.sqlite_research_note_repo import SQLiteResearchNoteRepository
from app.infrastructure.repositories.sqlite_timeline_event_repo import SQLiteTimelineEventRepository
from app.infrastructure.repositories.sqlite_workspace_settings_repo import SQLiteWorkspaceSettingsRepository
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
from app.domain.services.generation_service import GenerationService
from app.domain.services.citation_service import CitationService
from app.domain.services.response_validator import ResponseValidator
from app.application.services.rag_pipeline_service import RAGPipelineService



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


# ── Authentication Dependencies ───────────────────────────────────

async def get_current_user(
    authorization: Annotated[Optional[str], Header(include_in_schema=False)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> User:
    """
    FastAPI dependency to verify Firebase ID token and return the User entity.
    Syncs Firebase user details with SQLite.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization credentials",
        )
    
    token = authorization.split(" ")[1]
    try:
        decoded_claims = verify_firebase_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )
    
    uid = decoded_claims.get("uid")
    email = decoded_claims.get("email") or ""
    name = decoded_claims.get("name") or decoded_claims.get("display_name") or email.split("@")[0]
    
    user_repo = SQLiteUserRepository(session)
    user = await user_repo.get_by_firebase_uid(uid)
    if not user:
        # Check by email as fallback
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            existing_user.firebase_uid = uid
            user = await user_repo.update(existing_user)
        else:
            user = User(
                firebase_uid=uid,
                email=email,
                display_name=name,
            )
            user = await user_repo.create(user)
            
            # Shift ownership of dev-user-001 demo records to this first real user
            await session.execute(
                text("UPDATE documents SET user_id = :new_id WHERE user_id = 'dev-user-001'"),
                {"new_id": user.id}
            )
            await session.execute(
                text("UPDATE collections SET user_id = :new_id WHERE user_id = 'dev-user-001'"),
                {"new_id": user.id}
            )
            await session.execute(
                text("UPDATE conversations SET user_id = :new_id WHERE user_id = 'dev-user-001'"),
                {"new_id": user.id}
            )
            await session.commit()
            
    return user


async def get_current_user_id(
    current_user: Annotated[User, Depends(get_current_user)]
) -> str:
    """Dependency that returns the current authenticated user's local database UUID string."""
    return current_user.id


# ── Type Aliases ─────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Repository Factories ────────────────────────────────────────

def get_user_repo(session: DbSession) -> SQLiteUserRepository:
    """Per-request user repository."""
    return SQLiteUserRepository(session)


def get_research_note_repo(session: DbSession) -> SQLiteResearchNoteRepository:
    """Per-request research note repository."""
    return SQLiteResearchNoteRepository(session)


def get_timeline_event_repo(session: DbSession) -> SQLiteTimelineEventRepository:
    """Per-request timeline event repository."""
    return SQLiteTimelineEventRepository(session)


def get_workspace_settings_repo(session: DbSession) -> SQLiteWorkspaceSettingsRepository:
    """Per-request workspace settings repository."""
    return SQLiteWorkspaceSettingsRepository(session)


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


@lru_cache
def get_generation_service() -> GenerationService:
    """Singleton generation service."""
    provider = get_llm_provider()
    response_validator = ResponseValidator()
    return GenerationService(provider=provider, response_validator=response_validator)


@lru_cache
def get_citation_service() -> CitationService:
    """Singleton citation service."""
    return CitationService()


def get_rag_pipeline_service(
    document_repo: Annotated[SQLiteDocumentRepository, Depends(get_document_repo)],
    upload_use_case: Annotated[UploadDocumentUseCase, Depends(get_upload_document_use_case)],
    process_document_use_case: Annotated[ProcessDocumentUseCase, Depends(get_process_document_use_case)],
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    generation_service: Annotated[GenerationService, Depends(get_generation_service)],
    citation_service: Annotated[CitationService, Depends(get_citation_service)],
    file_storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
    parser_factory: Annotated[ParserFactory, Depends(get_parser_factory)],
    vector_store_service: Annotated[VectorStoreService, Depends(get_vector_store_service)],
) -> RAGPipelineService:
    """Per-request RAG pipeline service orchestrator."""
    return RAGPipelineService(
        document_repo=document_repo,
        upload_use_case=upload_use_case,
        process_document_use_case=process_document_use_case,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        citation_service=citation_service,
        file_storage=file_storage,
        parser_factory=parser_factory,
        vector_store_service=vector_store_service,
    )
