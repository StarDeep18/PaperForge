"""
API Middleware.

Error handling middleware that translates domain exceptions
into appropriate HTTP responses.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger
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

