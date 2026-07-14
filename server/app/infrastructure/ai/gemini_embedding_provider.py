"""
Gemini Embedding Provider.

Generates vector embeddings using Google Gemini API via LangChain.
"""

import asyncio
import math
import time
from typing import Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.services.embedding_provider import EmbeddingProvider
from app.domain.entities.embedding_result import EmbeddingResult
from app.domain.exceptions import (
    EmbeddingError,
    EmbeddingProviderUnavailable,
    EmbeddingTimeout,
    InvalidEmbeddingResponse,
)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Adapter for Google Gemini Embedding API.
    
    Includes API validation, retry orchestration, L2 normalization,
    and structured error mapping.
    """

    def __init__(self):
        settings = get_settings()
        self._provider_name = "gemini"
        self._target_dimension = settings.embedding_dimension
        
        # Initialize LangChain Google Gemini embedding wrapper
        # We model-prefix with "models/" as required by langchain-google-genai
        model_name = settings.embedding_model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
            
        self._model = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=settings.google_api_key,
        )
        logger.info(
            f"GeminiEmbeddingProvider initialized: model={model_name}, "
            f"target_dimension={self._target_dimension}"
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def dimension(self) -> int:
        return self._target_dimension

    def _normalize_vector(self, v: list[float]) -> list[float]:
        """Perform L2 normalization on a vector."""
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0.0:
            return v
        return [x / norm for x in v]

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        start_time = time.perf_counter()
        settings = get_settings()
        
        timeout = settings.embedding_timeout
        retries = settings.embedding_retry_count
        backoff = 1.0
        
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # Execute async call with timeout constraint
                vector = await asyncio.wait_for(
                    self._model.aembed_query(text),
                    timeout=timeout
                )
                
                if not vector:
                    raise InvalidEmbeddingResponse(
                        self.provider_name, 
                        "Received empty embedding vector from API."
                    )
                
                # Normalize if configured
                if settings.embedding_normalization:
                    vector = self._normalize_vector(vector)
                    
                duration = time.perf_counter() - start_time
                return EmbeddingResult(
                    success=True,
                    provider=self.provider_name,
                    dimension=len(vector),
                    vector=vector,
                    duration=duration,
                    warnings=[],
                )
                
            except asyncio.TimeoutError as e:
                last_error = EmbeddingTimeout(self.provider_name, timeout)
                logger.warning(
                    f"Gemini single embedding attempt {attempt + 1}/{retries + 1} timed out "
                    f"after {timeout}s."
                )
            except Exception as e:
                # Map standard API errors
                err_msg = str(e).lower()
                if "api_key" in err_msg or "apikey" in err_msg or "unauthorized" in err_msg:
                    last_error = InvalidEmbeddingResponse(self.provider_name, f"Authentication failed: {e}")
                elif "connection" in err_msg or "dns" in err_msg or "unavailable" in err_msg or "unreachable" in err_msg:
                    last_error = EmbeddingProviderUnavailable(self.provider_name, str(e))
                else:
                    last_error = EmbeddingError(f"Gemini API failure: {e}")
                    
                logger.warning(
                    f"Gemini single embedding attempt {attempt + 1}/{retries + 1} failed: {e}"
                )
                
            if attempt < retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
                
        # If all retries exhausted, raise the last encountered domain exception
        raise last_error or EmbeddingError("Unknown Gemini embedding generation failure")

    async def generate_batch_embeddings(self, texts: list[str]) -> EmbeddingResult:
        start_time = time.perf_counter()
        settings = get_settings()
        
        timeout = settings.embedding_timeout
        retries = settings.embedding_retry_count
        backoff = 1.0
        
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # Execute async call with timeout constraint
                vectors = await asyncio.wait_for(
                    self._model.aembed_documents(texts),
                    timeout=timeout
                )
                
                if not vectors or len(vectors) != len(texts):
                    raise InvalidEmbeddingResponse(
                        self.provider_name, 
                        f"Batch size mismatch: requested {len(texts)}, returned {len(vectors) if vectors else 0}"
                    )
                
                # Normalize if configured
                if settings.embedding_normalization:
                    vectors = [self._normalize_vector(v) for v in vectors]
                    
                duration = time.perf_counter() - start_time
                return EmbeddingResult(
                    success=True,
                    provider=self.provider_name,
                    dimension=len(vectors[0]) if vectors else 0,
                    vectors=vectors,
                    duration=duration,
                    warnings=[],
                )
                
            except asyncio.TimeoutError as e:
                last_error = EmbeddingTimeout(self.provider_name, timeout)
                logger.warning(
                    f"Gemini batch embedding attempt {attempt + 1}/{retries + 1} timed out "
                    f"after {timeout}s."
                )
            except Exception as e:
                err_msg = str(e).lower()
                if "api_key" in err_msg or "apikey" in err_msg or "unauthorized" in err_msg:
                    last_error = InvalidEmbeddingResponse(self.provider_name, f"Authentication failed: {e}")
                elif "connection" in err_msg or "dns" in err_msg or "unavailable" in err_msg or "unreachable" in err_msg:
                    last_error = EmbeddingProviderUnavailable(self.provider_name, str(e))
                else:
                    last_error = EmbeddingError(f"Gemini API failure: {e}")
                    
                logger.warning(
                    f"Gemini batch embedding attempt {attempt + 1}/{retries + 1} failed: {e}"
                )
                
            if attempt < retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0
                
        raise last_error or EmbeddingError("Unknown Gemini batch embedding generation failure")

    async def health_check(self) -> bool:
        """Verify connection to Google Gemini by generating a dummy embedding."""
        try:
            # Short timeout for quick health checking
            await asyncio.wait_for(self._model.aembed_query("health check"), timeout=5.0)
            return True
        except Exception as e:
            logger.error(f"Gemini embedding health check failed: {e}")
            return False
