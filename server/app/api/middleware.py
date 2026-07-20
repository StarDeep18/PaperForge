"""
API Middleware.

Error handling, correlation tracking, and logging wrappers.
"""

import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.logging import logger, request_id_var
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
    Translates domain exceptions to HTTP responses with a consistent JSON structure:
    {
        "error": "ErrorType",
        "message": "Friendly error message",
        "details": ...
    }
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": "Too many requests. Please try again later.",
                    "details": str(e),
                },
            )

        except ProviderHealthFailure as e:
            logger.error(f"Health check failed: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "ProviderHealthFailure",
                    "message": e.message,
                    "details": e.report,
                },
            )

        except (DocumentProcessingFailure, QuestionAnsweringFailure) as e:
            logger.error(f"Pipeline execution failure: {e.message}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": e.__class__.__name__,
                    "message": e.message,
                    "details": None,
                },
            )

        except PipelineInitializationFailure as e:
            logger.error(f"Pipeline initialization failure: {e.message}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "PipelineInitializationFailure",
                    "message": e.message,
                    "details": None,
                },
            )

        except RAGPipelineError as e:
            logger.error(f"Pipeline orchestration error: {e.message}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": e.__class__.__name__,
                    "message": e.message,
                    "details": None,
                },
            )

        except DocumentNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "DocumentNotFoundError",
                    "message": e.message,
                    "details": None,
                },
            )

        except CollectionNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "CollectionNotFoundError",
                    "message": e.message,
                    "details": None,
                },
            )

        except ConversationNotFoundError as e:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "ConversationNotFoundError",
                    "message": e.message,
                    "details": None,
                },
            )

        except UnsupportedFileTypeError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "UnsupportedFileTypeError",
                    "message": e.message,
                    "details": {"allowed": e.allowed},
                },
            )

        except FileTooLargeError as e:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "FileTooLargeError",
                    "message": e.message,
                    "details": {"max_bytes": e.max_bytes, "size_bytes": e.size_bytes},
                },
            )

        except DocumentProcessingError as e:
            logger.error(f"Processing error: {e.message}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": "DocumentProcessingError",
                    "message": e.message,
                    "details": None,
                },
            )

        except (EmbeddingError, LLMError, RetrievalError) as e:
            logger.error(f"AI error: {e.message}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": e.__class__.__name__,
                    "message": "AI service temporarily unavailable. Please try again.",
                    "details": {"reason": e.message},
                },
            )

        except PaperForgeError as e:
            logger.error(f"Domain error: {e.message}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": e.__class__.__name__,
                    "message": e.message,
                    "details": None,
                },
            )

        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An internal error occurred. Please try again.",
                    "details": str(e),
                },
            )


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates, reads, and writes correlation Request IDs to X-Request-ID headers,
    propagating the ID into logging contexts.
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
            return response
        finally:
            # 5. Clean up thread-local context
            request_id_var.reset(token)


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


