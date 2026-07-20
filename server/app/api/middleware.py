"""
API Middleware.

Error handling, correlation tracking, security compliance, and logging wrappers.
"""

import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.logging import logger, request_id_var
from app.core.config import get_settings
from app.domain.exceptions import (
    CollectionNotFoundError,
    ConversationNotFoundError,
    DocumentNotFoundError,
    DocumentProcessingError,
    EmbeddingError,
    FileTooLargeError,
    LLMError,
    PaperForgeError,
    RetrievalError,
    UnsupportedFileTypeError,
    RAGPipelineError,
    DocumentProcessingFailure,
    QuestionAnsweringFailure,
    PipelineInitializationFailure,
    ProviderHealthFailure,
)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Translates domain exceptions to HTTP responses with a consistent Production v2 JSON structure:
    {
        "code": "ERROR_CODE",
        "message": "Friendly error message",
        "request_id": "correlation-request-id",
        "details": ...
    }
    """

    async def dispatch(self, request: Request, call_next):
        req_id = request_id_var.get()

        try:
            response = await call_next(request)
            return response

        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                    "request_id": req_id,
                    "details": str(e),
                },
            )

        except ProviderHealthFailure as e:
            logger.error(f"Health check failed: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "code": "PROVIDER_HEALTH_FAILURE",
                    "message": e.message,
                    "request_id": req_id,
                    "details": e.report,
                },
            )

        except DocumentProcessingFailure as e:
            logger.error(f"Document processing execution failure: {e.message}")
            return JSONResponse(
                status_code=422,
                content={
                    "code": "DOCUMENT_PROCESSING_FAILED",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except QuestionAnsweringFailure as e:
            logger.error(f"Question answering execution failure: {e.message}")
            return JSONResponse(
                status_code=422,
                content={
                    "code": "QUESTION_ANSWERING_FAILED",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except PipelineInitializationFailure as e:
            logger.error(f"Pipeline initialization failure: {e.message}")
            return JSONResponse(
                status_code=500,
                content={
                    "code": "PIPELINE_INITIALIZATION_FAILED",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except RAGPipelineError as e:
            logger.error(f"Pipeline orchestration error: {e.message}")
            return JSONResponse(
                status_code=400,
                content={
                    "code": "RAG_PIPELINE_ERROR",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except DocumentNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except CollectionNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "COLLECTION_NOT_FOUND",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except ConversationNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except UnsupportedFileTypeError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": e.message,
                    "request_id": req_id,
                    "details": {"allowed": e.allowed},
                },
            )

        except FileTooLargeError as e:
            return JSONResponse(
                status_code=413,
                content={
                    "code": "FILE_TOO_LARGE",
                    "message": e.message,
                    "request_id": req_id,
                    "details": {"max_bytes": e.max_bytes, "size_bytes": e.size_bytes},
                },
            )

        except DocumentProcessingError as e:
            logger.error(f"Processing error: {e.message}")
            return JSONResponse(
                status_code=422,
                content={
                    "code": "DOCUMENT_PROCESSING_FAILED",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except EmbeddingError as e:
            logger.error(f"Embedding error: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "code": "EMBEDDING_PROVIDER_FAILED",
                    "message": "AI embedding service temporarily unavailable. Please try again.",
                    "request_id": req_id,
                    "details": {"reason": e.message},
                },
            )

        except LLMError as e:
            logger.error(f"LLM error: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "code": "LLM_PROVIDER_FAILED",
                    "message": "AI generation service temporarily unavailable. Please try again.",
                    "request_id": req_id,
                    "details": {"reason": e.message},
                },
            )

        except RetrievalError as e:
            logger.error(f"Retrieval error: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "code": "RETRIEVAL_FAILED",
                    "message": "AI retrieval service temporarily unavailable. Please try again.",
                    "request_id": req_id,
                    "details": {"reason": e.message},
                },
            )

        except PaperForgeError as e:
            logger.error(f"Domain error: {e.message}")
            return JSONResponse(
                status_code=400,
                content={
                    "code": "DOMAIN_ERROR",
                    "message": e.message,
                    "request_id": req_id,
                    "details": None,
                },
            )

        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal error occurred. Please try again.",
                    "request_id": req_id,
                    "details": str(e),
                },
            )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates, reads, and writes correlation Request IDs to X-Request-ID headers,
    propagating the ID into logging contexts. Also injects API Version headers.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Fetch or generate X-Request-ID
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # 2. Set context variable for logging
        token = request_id_var.set(req_id)
        try:
            # 3. Process request
            response = await call_next(request)
            # 4. Inject X-Request-ID header into outgoing response
            response.headers["X-Request-ID"] = req_id
            # 5. Inject API version header
            response.headers["X-API-Version"] = get_settings().app_version
            return response
        finally:
            # 6. Clean up thread-local context
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends recommended security headers to all outbound responses.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RequestLoggingAndTimingMiddleware(BaseHTTPMiddleware):
    """
    Logs incoming request details and tracks endpoint processing latency.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        logger.info(f"Incoming request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"│ Status: {response.status_code} │ Duration: {duration:.2f}ms"
            )
            return response
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Request crashed: {request.method} {request.url.path} "
                f"│ Duration: {duration:.2f}ms │ Error: {str(e)}"
            )
            raise



