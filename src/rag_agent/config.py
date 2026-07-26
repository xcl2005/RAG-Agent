"""Application configuration.

All deploy-time values are read from environment variables or ``.env``.  Keeping
configuration outside the codebase makes the same package usable on a laptop,
inside Docker, and in a hosted environment without leaking credentials.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings.

    The validation rules intentionally fail fast for invalid retrieval
    parameters. Silent configuration mistakes are especially expensive in RAG:
    the service may keep answering while retrieval quality has already degraded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM transport. Responses is the current OpenAI API; Chat Completions is
    # retained as an interoperability fallback for third-party providers.
    llm_api_mode: Literal["responses", "chat_completions"] = "responses"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-5.6-luna"
    llm_store_responses: bool = False
    max_plan_output_tokens: int = Field(default=600, ge=64, le=4000)
    max_answer_output_tokens: int = Field(default=1200, ge=64, le=8000)
    max_repair_output_tokens: int = Field(default=1200, ge=64, le=8000)

    # Vector and lexical stores.
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "rag_chunks_v2"
    sqlite_path: Path = Path("storage/rag.db")
    checkpoint_path: Path = Path("storage/checkpoints.db")

    # Local embedding/reranking models. They are loaded lazily so /health does
    # not block on a model download.
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    enable_reranker: bool = True
    reranker_score_mode: Literal["logit", "probability"] = "logit"

    # Ingestion.
    chunk_size: int = Field(default=900, ge=128, le=8000)
    chunk_overlap: int = Field(default=150, ge=0, le=2000)

    # Hybrid retrieval and weighted reciprocal-rank fusion.
    dense_top_k: int = Field(default=30, ge=1, le=200)
    sparse_top_k: int = Field(default=30, ge=1, le=200)
    fusion_top_k: int = Field(default=20, ge=1, le=100)
    rerank_top_k: int = Field(default=8, ge=1, le=50)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    dense_weight: float = Field(default=1.0, gt=0, le=10)
    sparse_weight: float = Field(default=1.0, gt=0, le=10)

    # Adaptive workflow and evidence gate. Reranker and fusion scores use
    # separate thresholds because they have different calibration.
    max_retrieval_attempts: int = Field(default=2, ge=1, le=4)
    max_query_variants: int = Field(default=3, ge=1, le=6)
    min_rerank_relevance: float = Field(default=0.55, ge=0, le=1)
    # BGE v1.5 cosine scores have a compressed, high baseline; 0.80 is a
    # deliberately conservative fallback when the cross-encoder is unavailable.
    # Tune this on the repository's labeled retrieval set before production use.
    min_dense_relevance: float = Field(default=0.80, ge=-1, le=1)
    min_sparse_coverage: float = Field(default=0.45, ge=0, le=1)
    max_context_chars: int = Field(default=12_000, ge=1000, le=100_000)

    # API, security, and local MCP transport.
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_allowed_hosts: str = "127.0.0.1,localhost,testserver"
    api_access_key: str = ""
    admin_api_key: str = ""
    max_question_chars: int = Field(default=4000, ge=64, le=100_000)
    max_upload_mb: int = Field(default=20, ge=1, le=500)
    max_upload_files: int = Field(default=10, ge=1, le=100)
    allowed_ingest_root: Path = Path("data/raw")
    log_level: str = "INFO"
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"

    @field_validator("openai_base_url", "qdrant_url")
    @classmethod
    def strip_url_suffix(cls, value: str) -> str:
        """Normalize URLs so later equality checks are predictable."""

        return value.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @model_validator(mode="after")
    def validate_retrieval_shape(self) -> Settings:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.rerank_top_k > self.fusion_top_k:
            raise ValueError("rerank_top_k cannot exceed fusion_top_k")
        return self

    @property
    def llm_enabled(self) -> bool:
        """Whether a model call can be attempted."""

        return bool(self.openai_api_key.strip())

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def allowed_hosts(self) -> list[str]:
        """Trusted Host allowlist used to reduce DNS-rebinding exposure."""

        values = [item.strip() for item in self.api_allowed_hosts.split(",") if item.strip()]
        if not values:
            raise ValueError("API_ALLOWED_HOSTS must contain at least one host")
        return values

    @property
    def is_official_openai_endpoint(self) -> bool:
        """Used only for diagnostics, never as an authorization decision."""

        return self.openai_base_url in {
            "https://api.openai.com/v1",
            "https://api.openai.com",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings once per process.

    Tests can call ``get_settings.cache_clear()`` after changing environment
    variables.  Existing imports can continue using the compatibility alias
    below.
    """

    return Settings()


settings = get_settings()
