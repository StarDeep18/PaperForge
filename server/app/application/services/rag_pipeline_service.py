"""
RAG Pipeline Service.

Application service serving as the single entry point for all AI and RAG interactions:
- Ingesting and processing documents
- Orchestrating question answering (Retrieval -> Generation -> Citation)
- Executing system health check diagnostics
"""

import time
from typing import Optional, Any, Dict
from app.core.logging import logger
from app.domain.entities.document import Document
from app.domain.entities.rag import (
    DocumentProcessingResult,
    RAGRequest,
    RAGResponse,
)
from app.domain.entities.retrieval import RetrievalRequest
from app.domain.entities.metadata_filter import MetadataFilter
from app.domain.entities.generation import GenerationRequest
from app.domain.repositories.document_repository import DocumentRepository
from app.application.documents.upload_document import UploadDocumentUseCase
from app.application.documents.process_document import ProcessDocumentUseCase
from app.domain.services.retrieval_service import RetrievalService
from app.domain.services.generation_service import GenerationService
from app.domain.services.citation_service import CitationService
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.infrastructure.parsing.parser_factory import ParserFactory
from app.domain.exceptions import (
    RAGPipelineError,
    DocumentProcessingFailure,
    QuestionAnsweringFailure,
    PipelineInitializationFailure,
    ProviderHealthFailure,
    PaperForgeError,
)

class RAGPipelineService:
    """
    Unified orchestration layer managing end-to-end Retrieval-Augmented Generation workflows.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        upload_use_case: UploadDocumentUseCase,
        process_document_use_case: ProcessDocumentUseCase,
        retrieval_service: RetrievalService,
        generation_service: GenerationService,
        citation_service: CitationService,
        file_storage: LocalFileStorage,
        parser_factory: ParserFactory,
    ):
        if not all([
            document_repo, upload_use_case, process_document_use_case,
            retrieval_service, generation_service, citation_service,
            file_storage, parser_factory
        ]):
            raise PipelineInitializationFailure("One or more dependencies were missing during RAGPipelineService initialization.")

        self._document_repo = document_repo
        self._upload_use_case = upload_use_case
        self._process_document_use_case = process_document_use_case
        self._retrieval_service = retrieval_service
        self._generation_service = generation_service
        self._citation_service = citation_service
        self._file_storage = file_storage
        self._parser_factory = parser_factory

    async def process_document(self, document: Document) -> DocumentProcessingResult:
        """
        Orchestrates full document parsing, chunking, embedding, and vector storage.
        """
        start_time = time.perf_counter()
        warnings = []
        errors = []
        doc_id = document.id

        try:
            # Process using the existing UseCase pipeline
            processed_doc = await self._process_document_use_case.execute(document)
            duration = time.perf_counter() - start_time

            result = DocumentProcessingResult(
                success=True,
                document_id=doc_id,
                pages=processed_doc.metadata.page_count if processed_doc.metadata else 0,
                chunks=processed_doc.chunk_count,
                embeddings=processed_doc.chunk_count,  # Each chunk has one embedding
                duration=duration,
                warnings=warnings,
            )

            # Structured logging
            logger.info(
                f"Document processing completed: "
                f"document_id={doc_id}, "
                f"processing_duration={duration:.4f}s, "
                f"total_duration={duration:.4f}s, "
                f"warnings={warnings}, "
                f"errors={errors}"
            )
            return result

        except Exception as e:
            duration = time.perf_counter() - start_time
            err_msg = str(e)
            errors.append(err_msg)
            logger.error(
                f"Document processing failed: "
                f"document_id={doc_id}, "
                f"processing_duration={duration:.4f}s, "
                f"total_duration={duration:.4f}s, "
                f"warnings={warnings}, "
                f"errors={errors}"
            )
            # Map exception
            if isinstance(e, PaperForgeError):
                raise DocumentProcessingFailure(f"Document processing failed: {e.message}") from e
            raise DocumentProcessingFailure(f"Document processing failed due to unexpected error: {err_msg}") from e

    async def answer_question(self, request: RAGRequest) -> RAGResponse:
        """
        Executes end-to-end question answering workflows by chaining:
        RetrievalService -> GenerationService -> CitationService
        """
        start_time = time.perf_counter()
        warnings = []
        errors = []

        # Validate request query
        if not request.query or not request.query.strip():
            raise QuestionAnsweringFailure("Query text cannot be empty.")

        try:
            # ── 1. Retrieval Layer ─────────────────────────────────────
            retrieval_start = time.perf_counter()
            ret_opts = request.retrieval_options or {}
            
            # Map workspace_id and document_ids
            doc_ids = ret_opts.get("document_ids")
            collection_id = ret_opts.get("collection_id")
            
            # Construct metadata filter
            m_filter = ret_opts.get("metadata_filter")
            if not isinstance(m_filter, MetadataFilter):
                # If a dict is provided or compile one
                m_filter = MetadataFilter(
                    document_ids=doc_ids,
                    collection_id=collection_id,
                    workspace_id=request.workspace_id
                )
            else:
                if doc_ids:
                    m_filter.document_ids = doc_ids
                if collection_id:
                    m_filter.collection_id = collection_id
                if request.workspace_id:
                    m_filter.workspace_id = request.workspace_id

            retrieval_req = RetrievalRequest(
                query=request.query,
                workspace_id=request.workspace_id,
                document_ids=doc_ids,
                metadata_filter=m_filter,
                top_k=ret_opts.get("top_k"),
                similarity_threshold=ret_opts.get("similarity_threshold"),
                max_context_tokens=ret_opts.get("max_context_tokens"),
            )

            retrieval_result = await self._retrieval_service.retrieve(retrieval_req)
            ret_duration = (time.perf_counter() - retrieval_start)
            
            # Collect warnings
            if retrieval_result.warnings:
                warnings.extend(retrieval_result.warnings)

            # Extract list of document ids referenced in this retrieval run
            retrieved_doc_ids = list(set(chunk.document_id for chunk in retrieval_result.retrieved_chunks)) if retrieval_result.retrieved_chunks else []

            # ── 2. Generation Layer ────────────────────────────────────
            generation_start = time.perf_counter()
            gen_opts = request.generation_options or {}
            generation_req = GenerationRequest(
                user_query=request.query,
                retrieval_result=retrieval_result,
                conversation_history=request.conversation_history or [],
                generation_options=gen_opts,
            )

            generation_result = await self._generation_service.generate(generation_req)
            gen_duration = generation_result.metrics.duration
            
            # Collect warnings
            if generation_result.warnings:
                warnings.extend(generation_result.warnings)

            # ── 3. Citation Layer ──────────────────────────────────────
            citation_start = time.perf_counter()
            citation_result = self._citation_service.generate_citations(
                answer=generation_result.response,
                retrieval_result=retrieval_result,
                grouping_policy=gen_opts.get("grouping_policy"),
                page_merge_policy=gen_opts.get("page_merge_policy"),
            )
            cit_duration = (time.perf_counter() - citation_start)
            
            # Collect warnings
            if citation_result.warnings:
                warnings.extend(citation_result.warnings)

            # Total duration
            total_duration = time.perf_counter() - start_time

            # Structured logging
            logger.info(
                f"RAG QA pipeline completed: "
                f"retrieval_duration={ret_duration:.4f}s, "
                f"generation_duration={gen_duration:.4f}s, "
                f"citation_duration={cit_duration:.4f}s, "
                f"total_duration={total_duration:.4f}s, "
                f"document_id={retrieved_doc_ids}, "
                f"query_length={len(request.query)}, "
                f"provider={generation_result.provider}, "
                f"warnings={warnings}, "
                f"errors={errors}"
            )

            return RAGResponse(
                answer=generation_result.response,
                citations=citation_result.citations,
                confidence=citation_result.overall_confidence,
                evidence_graph=citation_result.evidence_graph,
                retrieval_result=retrieval_result,
                generation_metrics=generation_result.metrics,
                prompt_inspector=generation_result.inspector,
                warnings=warnings,
            )

        except Exception as e:
            total_duration = time.perf_counter() - start_time
            err_msg = str(e)
            errors.append(err_msg)
            
            logger.error(
                f"RAG QA pipeline failed: "
                f"total_duration={total_duration:.4f}s, "
                f"query_length={len(request.query)}, "
                f"warnings={warnings}, "
                f"errors={errors}"
            )
            
            # Map exception
            if isinstance(e, PaperForgeError):
                raise QuestionAnsweringFailure(f"Question answering failed: {e.message}") from e
            raise QuestionAnsweringFailure(f"Question answering failed due to unexpected error: {err_msg}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        Queries status flags for all critical services and returns a unified report.
        """
        health_report = {}
        overall_healthy = True

        try:
            # 1. Upload Service
            try:
                upload_dir_exists = self._file_storage._upload_dir.exists()
                health_report["upload_service"] = "healthy" if upload_dir_exists else "unhealthy"
                health_report["Upload Service"] = health_report["upload_service"]
            except Exception as e:
                logger.error(f"Health check upload service failure: {e}")
                health_report["upload_service"] = "unhealthy"
                health_report["Upload Service"] = "unhealthy"
                overall_healthy = False

            # 2. Parser
            try:
                # Factory should have standard parsers ready
                parser_healthy = (
                    self._parser_factory._pdf_parser is not None and
                    self._parser_factory._docx_parser is not None
                )
                health_report["parser"] = "healthy" if parser_healthy else "unhealthy"
                health_report["Parser"] = health_report["parser"]
            except Exception as e:
                logger.error(f"Health check parser failure: {e}")
                health_report["parser"] = "unhealthy"
                health_report["Parser"] = "unhealthy"
                overall_healthy = False

            # 3. Embedding Provider
            try:
                emb_ok = await self._retrieval_service._embedding_provider.health_check()
                health_report["embedding_provider"] = "healthy" if emb_ok else "unhealthy"
                health_report["Embedding Provider"] = health_report["embedding_provider"]
            except Exception as e:
                logger.error(f"Health check embedding provider failure: {e}")
                health_report["embedding_provider"] = "unhealthy"
                health_report["Embedding Provider"] = "unhealthy"
                overall_healthy = False

            # 4. Vector Store
            try:
                vs_check = await self._retrieval_service._vector_store_service.health_check()
                health_report["vector_store"] = vs_check.get("status", "unhealthy")
                health_report["Vector Store"] = health_report["vector_store"]
            except Exception as e:
                logger.error(f"Health check vector store failure: {e}")
                health_report["vector_store"] = "unhealthy"
                health_report["Vector Store"] = "unhealthy"
                overall_healthy = False

            # 5. Retrieval
            # Healthy if both vector store and embedding provider are healthy
            retrieval_healthy = (
                health_report.get("embedding_provider") == "healthy" and
                health_report.get("vector_store") == "healthy"
            )
            health_report["retrieval"] = "healthy" if retrieval_healthy else "unhealthy"
            health_report["Retrieval"] = health_report["retrieval"]

            # 6. Generation
            try:
                gen_ok = await self._generation_service.provider.health_check()
                health_report["generation"] = "healthy" if gen_ok else "unhealthy"
                health_report["Generation"] = health_report["generation"]
            except Exception as e:
                logger.error(f"Health check generation failure: {e}")
                health_report["generation"] = "unhealthy"
                health_report["Generation"] = "unhealthy"
                overall_healthy = False

            # 7. Citation
            # Citation service is local-only, so if instantiated it's healthy
            health_report["citation"] = "healthy"
            health_report["Citation"] = "healthy"

            # 8. Overall Status
            # Check if any component is unhealthy
            for k in ["upload_service", "parser", "embedding_provider", "vector_store", "retrieval", "generation", "citation"]:
                if health_report.get(k) != "healthy":
                    overall_healthy = False
                    break
            
            health_report["overall_status"] = "healthy" if overall_healthy else "unhealthy"
            health_report["Overall Status"] = health_report["overall_status"]

            if not overall_healthy:
                raise ProviderHealthFailure("One or more services reported unhealthy status.", health_report)

            return health_report

        except ProviderHealthFailure:
            raise
        except Exception as e:
            logger.error(f"Health check pipeline failure: {e}")
            health_report["overall_status"] = "unhealthy"
            health_report["Overall Status"] = "unhealthy"
            raise ProviderHealthFailure(f"Pipeline health check execution failed: {str(e)}", health_report) from e
