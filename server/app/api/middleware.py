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
)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Translates domain exceptions to HTTP responses.

    This keeps endpoint code clean — they can raise domain
    exceptions directly without manual HTTP error construction.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except DocumentNotFoundError as e:
            return JSONResponse(status_code=404, content={"detail": e.message})

        except CollectionNotFoundError as e:
            return JSONResponse(status_code=404, content={"detail": e.message})

        except ConversationNotFoundError as e:
            return JSONResponse(status_code=404, content={"detail": e.message})

        except UnsupportedFileTypeError as e:
            return JSONResponse(status_code=400, content={"detail": e.message})

        except FileTooLargeError as e:
            return JSONResponse(status_code=413, content={"detail": e.message})

        except DocumentProcessingError as e:
            logger.error(f"Processing error: {e.message}")
            return JSONResponse(status_code=422, content={"detail": e.message})

        except (EmbeddingError, LLMError, RetrievalError) as e:
            logger.error(f"AI error: {e.message}")
            return JSONResponse(
                status_code=503,
                content={"detail": "AI service temporarily unavailable. Please try again."},
            )

        except PaperForgeError as e:
            logger.error(f"Domain error: {e.message}")
            return JSONResponse(status_code=400, content={"detail": e.message})

        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal error occurred. Please try again."},
            )
