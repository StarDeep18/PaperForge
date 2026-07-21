"""
PaperForge Core Configuration.

Uses Pydantic Settings to load configuration from environment variables
with sensible defaults. All secrets and configurable values are managed here.
"""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "PaperForge"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    firebase_credentials_path: str = ""

    # ── Server ───────────────────────────────────────────────────
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/paperforge.db"

    # ── Vector Database ──────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "paperforge_chunks"
    vector_store_batch_size: int = 100
    vector_store_distance_metric: str = "cosine"  # cosine, l2, or ip
    vector_store_top_k_default: int = 8


    # ── Google Gemini & LLM Generation ───────────────────────────
    google_api_key: str = ""
    llm_provider: str = "gemini"  # "gemini" or "mock"
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.3
    llm_max_output_tokens: int = 4096
    llm_timeout: float = 30.0  # seconds
    llm_retry_count: int = 3
    llm_max_prompt_tokens: int = 8000

    embedding_model: str = "text-embedding-004"
    embedding_provider: str = "gemini"  # "gemini" or "mock"
    embedding_batch_size: int = 50
    embedding_timeout: float = 30.0  # seconds
    embedding_retry_count: int = 3
    embedding_max_concurrency: int = 5
    embedding_normalization: bool = True
    embedding_dimension: int = 768  # text-embedding-004 produces 768-dim vectors


    # ── Document Processing ──────────────────────────────────────
    max_upload_size_mb: int = 50
    upload_dir: str = "./uploads"
    allowed_extensions: str = ".pdf,.docx,.txt"

    # ── Chunking ─────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 50
    parent_chunk_size: int = 1500
    parent_chunk_overlap: int = 150

    # ── Retrieval ────────────────────────────────────────────────
    top_k_results: int = 8
    similarity_threshold: float = 0.3
    retrieval_default_top_k: int = 8
    retrieval_minimum_similarity: float = 0.3
    retrieval_max_context_tokens: int = 4000
    retrieval_duplicate_threshold: float = 0.85  # cosine threshold above which chunks are duplicates
    retrieval_chunk_merge_policy: str = "merge_parent"  # "merge_parent" or "none"

    # ── Citation Engine ──────────────────────────────────────────
    citation_min_confidence: float = 0.3
    citation_grouping: str = "document"  # "document" or "page"
    citation_page_merge_policy: str = "consecutive"  # "consecutive" or "none"
    citation_max_snippet_length: int = 200
    citation_high_confidence_threshold: float = 0.7
    citation_medium_confidence_threshold: float = 0.4


    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extension_list(self) -> list[str]:
        """Parse allowed file extensions from comma-separated string."""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes for file upload validation."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        """Resolved data directory path for SQLite."""
        path = Path("./data")
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings factory.

    Returns the same Settings instance on every call, avoiding
    redundant environment variable parsing.
    """
    return Settings()
