from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Manutencao Prescritiva Enterprise"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://maintenance:maintenance@db:5432/maintenance"
    sync_database_url: str = "postgresql+psycopg://maintenance:maintenance@db:5432/maintenance"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 600

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    document_min_similarity: float = 0.42
    event_similarity_limit: int = 20
    event_max_distance: float = 0.35
    hybrid_vector_weight: float = 0.70
    hybrid_text_weight: float = 0.30

    llm_provider: str = "template"
    llm_base_url: str = "http://host.docker.internal:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout_seconds: int = 60

    model_artifact_dir: Path = Path("artifacts")
    banner_csv_path: Path = Path("data/banner.csv")
    documents_dir: Path = Path("data/documents")

    enable_otel: bool = False
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
