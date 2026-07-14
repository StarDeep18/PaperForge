"""
Embedding Provider.

Wraps the Google Gemini embedding API via LangChain for generating
vector embeddings of text chunks and queries.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import get_settings
from app.core.logging import logger
from app.domain.exceptions import EmbeddingError


class EmbeddingProvider:
    """
    Generates text embeddings using Google Gemini.

    Uses task_type hints to improve retrieval quality:
    - "retrieval_document" for indexing document chunks
    - "retrieval_query" for embedding search queries
    """

    def __init__(self):
        settings = get_settings()
        self._model = GoogleGenerativeAIEmbeddings(
            model=f"models/{settings.embedding_model}",
            google_api_key=settings.google_api_key,
        )
        logger.info(f"Embedding provider initialized: model={settings.embedding_model}")

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for document chunks.

        Args:
            texts: List of text chunks to embed.

        Returns:
            List of embedding vectors.
        """
        try:
            embeddings = self._model.embed_documents(texts)
            logger.info(f"Generated {len(embeddings)} document embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(str(e)) from e

    async def embed_query(self, text: str) -> list[float]:
        """
        Generate an embedding for a search query.

        Uses the "retrieval_query" task type for optimal
        query-document matching.

        Args:
            text: The query text to embed.

        Returns:
            The query embedding vector.
        """
        try:
            embedding = self._model.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            raise EmbeddingError(str(e)) from e
