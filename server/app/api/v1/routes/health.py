"""
API v1 Health Router.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_rag_pipeline_service
from app.application.services.rag_pipeline_service import RAGPipelineService
from app.api.v1.models.responses import HealthResponse

router = APIRouter(prefix="/health", tags=["System"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Get pipeline health",
    description="Proactively audits and reports the connectivity and status of all critical RAG sub-services (storage, parser, embeddings, database, LLM provider, etc.).",
)
async def check_health(
    pipeline_service: RAGPipelineService = Depends(get_rag_pipeline_service),
):
    # health_check() will return the report dictionary or raise ProviderHealthFailure
    # which is handled and mapped by the ErrorHandlingMiddleware.
    report = await pipeline_service.health_check()
    return HealthResponse(
        upload_service=report["upload_service"],
        parser=report["parser"],
        embedding_provider=report["embedding_provider"],
        vector_store=report["vector_store"],
        retrieval=report["retrieval"],
        generation=report["generation"],
        citation=report["citation"],
        overall_status=report["overall_status"],
    )
