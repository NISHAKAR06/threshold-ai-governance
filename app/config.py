"""
config.py — THRESHOLD AI Governance Platform
Centralised application configuration via environment variables.
"""
import os
from pathlib import Path
from functools import lru_cache
from typing import List, Optional
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=_BASE_DIR.parent / ".env")


class Settings:
    # ── App ──────────────────────────────────────────────────
    APP_NAME: str         = "THRESHOLD AI Governance"
    APP_VERSION: str      = os.getenv("APP_VERSION", "2.0.0")
    DEBUG: bool           = os.getenv("DEBUG", "true").lower() == "true"
    ENABLE_DOCS: bool     = os.getenv("ENABLE_DOCS", "true").lower() == "true"
    SECRET_KEY: str       = os.getenv("SECRET_KEY", "THRESHOLD-secret-change-in-production-x9k2p")

    # ── Server ───────────────────────────────────────────────
    HOST: str             = os.getenv("HOST", "0.0.0.0")
    PORT: int             = int(os.getenv("PORT", "8000"))

    # ── Paths ─────────────────────────────────────────────────
    BASE_DIR: Path        = Path(__file__).parent
    STATIC_DIR: Path      = BASE_DIR / "static"
    TEMPLATES_DIR: Path   = BASE_DIR / "templates"

    # ── Database ──────────────────────────────────────────────
    # Defaults to SQLite for local dev; set DATABASE_URL in .env for PostgreSQL
    _default_db_path: Path = BASE_DIR.parent / "THRESHOLD.db"
    DATABASE_URL: str     = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_default_db_path}"
    )
    DATABASE_ECHO: bool   = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int     = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int  = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # ── Alembic (sync URL for migrations) ─────────────────────
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        f"sqlite:///{_default_db_path}"
    )

    # ── JWT Auth ──────────────────────────────────────────────
    JWT_SECRET: str       = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ALGORITHM: str    = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # ── Gemini LLM ────────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str     = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int   = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TIMEOUT: int      = int(os.getenv("LLM_TIMEOUT", "120"))

    # ── Risk Thresholds ───────────────────────────────────────
    AUTO_APPROVE_THRESHOLD: int   = int(os.getenv("AUTO_APPROVE_THRESHOLD", "30"))
    CONFIRM_THRESHOLD: int        = int(os.getenv("CONFIRM_THRESHOLD", "60"))
    HUMAN_REVIEW_THRESHOLD: int   = int(os.getenv("HUMAN_REVIEW_THRESHOLD", "80"))

    # ── Adaptive Learning ─────────────────────────────────────
    LEARNING_RATE: float  = float(os.getenv("LEARNING_RATE", "0.1"))
    LEARNING_ENABLED: bool = os.getenv("LEARNING_ENABLED", "true").lower() == "true"
    MIN_SAMPLES_TO_LEARN: int = int(os.getenv("MIN_SAMPLES_TO_LEARN", "5"))

    # ── WebSocket ─────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

    # ── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

    # ── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str        = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str       = "json"

    # ── Business rules ────────────────────────────────────────
    BUSINESS_HOURS_START: int = int(os.getenv("BUSINESS_HOURS_START", "9"))
    BUSINESS_HOURS_END: int   = int(os.getenv("BUSINESS_HOURS_END", "18"))
    PROTECTED_TABLES: List[str] = ["employees", "settings", "audit_logs"]
    RESTRICTED_OPERATIONS: List[str] = ["DELETE", "TRUNCATE", "DROP"]

    # ── i18n ─────────────────────────────────────────────────
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")

    # ── Chunking (Phase 9) ───────────────────────────────────
    CHUNK_SIZE: int       = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int    = int(os.getenv("CHUNK_OVERLAP", "150"))

    @staticmethod
    def validate_chunk_config(chunk_size: int, chunk_overlap: int) -> None:
        """Validate chunk size and overlap configuration."""
        if chunk_size <= 0:
            raise ValueError(f"CHUNK_SIZE must be greater than 0, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"CHUNK_OVERLAP must be greater than or equal to 0, got {chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({chunk_overlap}) must be strictly smaller than CHUNK_SIZE ({chunk_size})"
            )

    # ── Embeddings & Vector Index (Phase 10) ─────────────────
    EMBEDDING_PROVIDER: str     = os.getenv("EMBEDDING_PROVIDER", "mock")
    EMBEDDING_MODEL: str        = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    EMBEDDING_BATCH_SIZE: int   = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    VECTOR_STORE_PROVIDER: str  = os.getenv("VECTOR_STORE_PROVIDER", "chroma")
    VECTOR_STORE_PATH: str      = os.getenv("VECTOR_STORE_PATH", "data/vector_store")
    VECTOR_STORE_COLLECTION: str = os.getenv("VECTOR_STORE_COLLECTION", "threshold_enterprise_chunks")

    @staticmethod
    def validate_embedding_config(
        provider: str,
        model: str,
        batch_size: int,
        vector_store_provider: str,
    ) -> None:
        """Validate embedding and vector store configuration."""
        valid_providers = {"mock", "gemini", "local"}
        if provider.lower() not in valid_providers:
            raise ValueError(f"Unsupported EMBEDDING_PROVIDER '{provider}'. Allowed: {valid_providers}")

        if not model or not model.strip():
            raise ValueError("EMBEDDING_MODEL cannot be empty")

        if batch_size <= 0:
            raise ValueError(f"EMBEDDING_BATCH_SIZE must be greater than 0, got {batch_size}")

        valid_stores = {"chroma", "in_memory", "json"}
        if vector_store_provider.lower() not in valid_stores:
            raise ValueError(
                f"Unsupported VECTOR_STORE_PROVIDER '{vector_store_provider}'. Allowed: {valid_stores}"
            )

    # ── Semantic Retrieval (Phase 11) ────────────────────────
    RETRIEVAL_DEFAULT_TOP_K: int    = int(os.getenv("RETRIEVAL_DEFAULT_TOP_K", "5"))
    RETRIEVAL_MAX_TOP_K: int        = int(os.getenv("RETRIEVAL_MAX_TOP_K", "20"))
    RETRIEVAL_MIN_QUERY_LENGTH: int = int(os.getenv("RETRIEVAL_MIN_QUERY_LENGTH", "2"))
    RETRIEVAL_MAX_QUERY_LENGTH: int = int(os.getenv("RETRIEVAL_MAX_QUERY_LENGTH", "1000"))

    @staticmethod
    def validate_retrieval_config(default_top_k: int, max_top_k: int) -> None:
        """Validate semantic retrieval configuration."""
        if default_top_k <= 0:
            raise ValueError(f"RETRIEVAL_DEFAULT_TOP_K must be greater than 0, got {default_top_k}")
        if max_top_k < default_top_k:
            raise ValueError(
                f"RETRIEVAL_MAX_TOP_K ({max_top_k}) must be greater than or equal to "
                f"RETRIEVAL_DEFAULT_TOP_K ({default_top_k})"
            )

    # ── Hybrid Search & Governance-Aware Retrieval (Phase 12) ───
    KEYWORD_SEARCH_ENABLED: bool             = os.getenv("KEYWORD_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
    HYBRID_FUSION_STRATEGY: str             = os.getenv("HYBRID_FUSION_STRATEGY", "RRF").upper()
    HYBRID_RRF_K: int                       = int(os.getenv("HYBRID_RRF_K", "60"))
    HYBRID_CANDIDATE_MULTIPLIER: int        = int(os.getenv("HYBRID_CANDIDATE_MULTIPLIER", "3"))
    GOVERNANCE_STRICT_DEPARTMENT_CHECK: bool = os.getenv("GOVERNANCE_STRICT_DEPARTMENT_CHECK", "false").lower() in ("true", "1", "yes")

    @staticmethod
    def validate_governance_retrieval_config(
        fusion_strategy: str,
        rrf_k: int,
        candidate_multiplier: int,
    ) -> None:
        """Validate hybrid and governance retrieval configuration."""
        valid_strategies = {"RRF", "RECIPROCAL_RANK_FUSION", "LINEAR", "WEIGHTED"}
        if fusion_strategy.upper() not in valid_strategies:
            raise ValueError(
                f"Unsupported HYBRID_FUSION_STRATEGY '{fusion_strategy}'. Allowed: {valid_strategies}"
            )
        if rrf_k <= 0:
            raise ValueError(f"HYBRID_RRF_K must be greater than 0, got {rrf_k}")
    # ── Governance-Aware RAG Answer Generation (Phase 13) ────────
    LLM_PROVIDER: str           = os.getenv("LLM_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "mock").lower()
    LLM_MODEL: str              = os.getenv("LLM_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    RAG_MAX_CONTEXT_CHUNKS: int = int(os.getenv("RAG_MAX_CONTEXT_CHUNKS", "5"))
    RAG_MAX_CONTEXT_LENGTH: int = int(os.getenv("RAG_MAX_CONTEXT_LENGTH", "8000"))
    RAG_MAX_ANSWER_LENGTH: int  = int(os.getenv("RAG_MAX_ANSWER_LENGTH", "2000"))
    RAG_TEMPERATURE: float      = float(os.getenv("RAG_TEMPERATURE", "0.2"))

    @staticmethod
    def validate_rag_config(
        provider: str,
        max_chunks: int,
        max_context_length: int,
        max_answer_length: int,
    ) -> None:
        """Validate RAG configuration parameters."""
        valid_providers = {"mock", "gemini"}
        if provider.lower() not in valid_providers:
            raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Allowed: {valid_providers}")
        if max_chunks <= 0:
            raise ValueError(f"RAG_MAX_CONTEXT_CHUNKS must be greater than 0, got {max_chunks}")
    # ── Controlled AI Agent & Governance Workflow (Phase 14) ────
    AGENT_ROUTING_STRATEGY: str  = os.getenv("AGENT_ROUTING_STRATEGY", "RULE_BASED").upper()
    AGENT_ENABLED_TOOLS: List[str] = [
        t.strip()
        for t in os.getenv(
            "AGENT_ENABLED_TOOLS",
            "RAG_QUESTION,RETRIEVAL_SEARCH,GOVERNANCE_EVALUATION",
        ).split(",")
        if t.strip()
    ]
    AGENT_AUDIT_ENABLED: bool     = os.getenv("AGENT_AUDIT_ENABLED", "true").lower() in ("true", "1", "yes")
    AGENT_MAX_REQUEST_LENGTH: int = int(os.getenv("AGENT_MAX_REQUEST_LENGTH", "4000"))

    @staticmethod
    def validate_agent_config(
        routing_strategy: str,
        enabled_tools: List[str],
        max_request_length: int,
    ) -> None:
        """Validate agent configuration parameters."""
        valid_strategies = {"RULE_BASED", "STRUCTURED_LLM"}
        if routing_strategy.upper() not in valid_strategies:
            raise ValueError(
                f"Unsupported AGENT_ROUTING_STRATEGY '{routing_strategy}'. Allowed: {valid_strategies}"
            )
        if not enabled_tools:
            raise ValueError("AGENT_ENABLED_TOOLS must not be empty.")
        if max_request_length <= 0:
            raise ValueError(f"AGENT_MAX_REQUEST_LENGTH must be greater than 0, got {max_request_length}")

    # ── Production Readiness & Observability (Phase 15) ─────────
    ENVIRONMENT: str              = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
    METRICS_ENABLED: bool         = os.getenv("METRICS_ENABLED", "true").lower() in ("true", "1", "yes")
    METRICS_PATH: str             = os.getenv("METRICS_PATH", "/metrics")
    TRACE_HEADER: str             = os.getenv("TRACE_HEADER", "X-Request-ID")
    
    # ── Responsible AI Controls (Phase 15) ─────────────────────
    RAI_ENABLED: bool                     = os.getenv("RAI_ENABLED", "true").lower() in ("true", "1", "yes")
    RAI_MAX_INPUT_LENGTH: int             = int(os.getenv("RAI_MAX_INPUT_LENGTH", "4000"))
    RAI_INJECTION_DETECTION_ENABLED: bool = os.getenv("RAI_INJECTION_DETECTION_ENABLED", "true").lower() in ("true", "1", "yes")
    RAI_STRICT_MODE: bool                 = os.getenv("RAI_STRICT_MODE", "false").lower() in ("true", "1", "yes")
    RAI_OUTPUT_VALIDATION_ENABLED: bool   = os.getenv("RAI_OUTPUT_VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes")

    @staticmethod
    def validate_production_config(cfg: "Settings") -> None:
        """
        Validate critical configuration for production deployment.
        Never reveals secret values in error messages.
        """
        if cfg.ENVIRONMENT in ("production", "prod"):
            insecure_keys = {
                "THRESHOLD-secret-change-in-production-x9k2p",
                "secret",
                "changeme",
                "default",
            }
            if not cfg.SECRET_KEY or cfg.SECRET_KEY in insecure_keys:
                raise ValueError("Insecure or default SECRET_KEY detected in production environment.")
            if not cfg.JWT_SECRET or cfg.JWT_SECRET in insecure_keys:
                raise ValueError("Insecure or default JWT_SECRET detected in production environment.")

        if cfg.RAI_MAX_INPUT_LENGTH <= 0:
            raise ValueError(f"RAI_MAX_INPUT_LENGTH must be > 0, got {cfg.RAI_MAX_INPUT_LENGTH}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

