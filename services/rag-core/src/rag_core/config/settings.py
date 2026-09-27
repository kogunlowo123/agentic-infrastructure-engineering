"""Configuration settings for RAG Core service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://agentic_app:password@localhost:5432/agentic_infra"

    # OpenSearch
    opensearch_url: str = "http://opensearch:9200"
    opensearch_index: str = "iac_documents"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"

    # Embeddings
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dim: int = 1024
    use_vertex_embeddings: bool = False

    # Vertex AI
    vertex_ai_location: str = "us-central1"
    gcp_project_id: str = ""

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval
    top_k: int = 10
    rerank_top_k: int = 3

    # PgVector
    pgvector_collection: str = "iac_documents"

    # Redis cache
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600

    # Logging
    log_level: str = "INFO"
    environment: str = "dev"


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
