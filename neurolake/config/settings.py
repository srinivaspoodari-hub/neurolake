"""
NeuroLake Configuration Settings

Comprehensive configuration management using Pydantic Settings.
All settings can be configured via environment variables with NEUROLAKE_ prefix.

Example:
    NEUROLAKE_DATABASE__HOST=localhost
    NEUROLAKE_DATABASE__PORT=5432
    NEUROLAKE_LLM__OPENAI__API_KEY=sk-...
"""

from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


# =============================================================================
# Database Settings
# =============================================================================

class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_DATABASE_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Connection
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port", ge=1, le=65535)
    database: str = Field(default="neurolake", description="Database name")
    username: str = Field(default="neurolake", description="Database user")
    password: str = Field(default="dev_password_change_in_prod", description="Database password")

    # Connection Pool
    pool_size: int = Field(default=20, description="Connection pool size", ge=1, le=100)
    max_overflow: int = Field(default=10, description="Max connection overflow", ge=0, le=100)
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds", ge=1)
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds", ge=60)

    # Performance
    echo_sql: bool = Field(default=False, description="Echo SQL queries to stdout")
    statement_timeout: int = Field(default=60000, description="Statement timeout in ms", ge=1000)

    # SSL
    sslmode: str = Field(default="prefer", description="SSL mode: disable, allow, prefer, require")
    sslcert: Optional[str] = Field(default=None, description="SSL certificate path")
    sslkey: Optional[str] = Field(default=None, description="SSL key path")

    @computed_field
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @computed_field
    @property
    def async_connection_string(self) -> str:
        """Generate async SQLAlchemy connection string"""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


# =============================================================================
# Storage Settings (MinIO/S3)
# =============================================================================

class StorageSettings(BaseSettings):
    """Object storage configuration (MinIO/S3)"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_STORAGE_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Connection
    endpoint: str = Field(default="localhost:9000", description="MinIO/S3 endpoint")
    access_key: str = Field(default="neurolake", description="Access key")
    secret_key: str = Field(default="dev_password_change_in_prod", description="Secret key")
    secure: bool = Field(default=False, description="Use HTTPS")
    region: str = Field(default="us-east-1", description="S3 region")

    # Buckets
    data_bucket: str = Field(default="data", description="Main data bucket")
    temp_bucket: str = Field(default="temp", description="Temporary data bucket")
    archive_bucket: str = Field(default="archive", description="Archive bucket")

    # Performance
    multipart_threshold: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Multipart upload threshold in bytes",
        ge=5 * 1024 * 1024,  # Min 5MB
    )
    max_concurrency: int = Field(default=10, description="Max concurrent uploads", ge=1, le=50)

    # Paths
    ncf_prefix: str = Field(default="ncf/", description="NCF files prefix")
    temp_prefix: str = Field(default="temp/", description="Temporary files prefix")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Ensure endpoint doesn't have protocol"""
        return v.replace("http://", "").replace("https://", "")


# =============================================================================
# Redis Settings
# =============================================================================

class RedisSettings(BaseSettings):
    """Redis cache configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_REDIS_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Connection
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port", ge=1, le=65535)
    db: int = Field(default=0, description="Redis database number", ge=0, le=15)
    password: Optional[str] = Field(default=None, description="Redis password")

    # Connection Pool
    max_connections: int = Field(default=50, description="Max connections", ge=1, le=1000)
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds", ge=1)
    socket_connect_timeout: int = Field(default=5, description="Connect timeout in seconds", ge=1)

    # Performance
    decode_responses: bool = Field(default=True, description="Decode responses to strings")

    # Cache TTL (in seconds)
    default_ttl: int = Field(default=3600, description="Default cache TTL", ge=60)
    query_result_ttl: int = Field(default=1800, description="Query result cache TTL", ge=60)
    metadata_ttl: int = Field(default=7200, description="Metadata cache TTL", ge=300)


# =============================================================================
# Qdrant Settings
# =============================================================================

class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_QDRANT_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Connection
    host: str = Field(default="localhost", description="Qdrant host")
    port: int = Field(default=6333, description="Qdrant HTTP port", ge=1, le=65535)
    grpc_port: int = Field(default=6334, description="Qdrant gRPC port", ge=1, le=65535)
    api_key: Optional[str] = Field(default=None, description="Qdrant API key")

    # Collections
    embeddings_collection: str = Field(default="neurolake_embeddings", description="Embeddings collection")
    vector_size: int = Field(default=1536, description="Vector dimension size", ge=128)

    # Performance
    prefer_grpc: bool = Field(default=True, description="Prefer gRPC over HTTP")
    timeout: int = Field(default=60, description="Request timeout in seconds", ge=5)


# =============================================================================
# LLM Settings
# =============================================================================

class OpenAISettings(BaseSettings):
    """OpenAI API configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_LLM_OPENAI_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    organization: Optional[str] = Field(default=None, description="OpenAI organization")
    model: str = Field(default="gpt-4-turbo-preview", description="Default model")
    embedding_model: str = Field(default="text-embedding-3-large", description="Embedding model")
    temperature: float = Field(default=0.7, description="Temperature", ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, description="Max tokens", ge=1, le=128000)
    timeout: int = Field(default=60, description="Request timeout in seconds", ge=5)


class AnthropicSettings(BaseSettings):
    """Anthropic API configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_LLM_ANTHROPIC_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    model: str = Field(default="claude-3-5-sonnet-20241022", description="Default model")
    temperature: float = Field(default=0.7, description="Temperature", ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, description="Max tokens", ge=1, le=200000)
    timeout: int = Field(default=60, description="Request timeout in seconds", ge=5)


class LLMSettings(BaseSettings):
    """LLM configuration"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_LLM_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Provider selection
    default_provider: str = Field(
        default="openai",
        description="Default LLM provider: openai, anthropic",
    )

    # Sub-settings
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)

    # Rate limiting
    max_requests_per_minute: int = Field(default=50, description="Max requests/min", ge=1)
    max_concurrent_requests: int = Field(default=5, description="Max concurrent", ge=1, le=20)

    @field_validator("default_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name"""
        if v.lower() not in ["openai", "anthropic"]:
            raise ValueError("Provider must be 'openai' or 'anthropic'")
        return v.lower()


# =============================================================================
# API Settings
# =============================================================================

class APISettings(BaseSettings):
    """FastAPI application settings"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_API_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Server
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port", ge=1, le=65535)
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    workers: int = Field(default=4, description="Worker processes", ge=1, le=32)
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")

    # Security
    secret_key: str = Field(
        default="dev_secret_key_change_in_production_use_openssl_rand_hex_32",
        description="Secret key for JWT"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration",
        ge=5,
        le=1440
    )
    allowed_hosts: List[str] = Field(
        default=["*"],
        description="Allowed hosts for production"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per window", ge=1)
    rate_limit_window: int = Field(default=60, description="Window in seconds", ge=1)
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute", ge=1)

    # Documentation
    docs_url: str = Field(default="/docs", description="Swagger UI path")
    redoc_url: str = Field(default="/redoc", description="ReDoc path")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI schema path")


# =============================================================================
# Monitoring Settings
# =============================================================================

class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_MONITORING_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus export")
    metrics_port: int = Field(default=9090, description="Metrics port", ge=1, le=65535)

    # Tracing
    enable_tracing: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")
    jaeger_host: str = Field(default="localhost", description="Jaeger host")
    jaeger_port: int = Field(default=6831, description="Jaeger port", ge=1, le=65535)

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format: json, text")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


# =============================================================================
# Main Settings
# =============================================================================

class Settings(BaseSettings):
    """Main NeuroLake settings"""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Application
    app_name: str = Field(default="NeuroLake", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    api: APISettings = Field(default_factory=APISettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Local data directory")
    cache_dir: Path = Field(default=Path("./.cache"), description="Cache directory")
    logs_dir: Path = Field(default=Path("./logs"), description="Logs directory")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment"""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()

    def model_post_init(self, __context: Any) -> None:
        """Create directories after initialization"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


# =============================================================================
# Settings Instance
# =============================================================================

# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern)

    Returns:
        Settings: Global settings instance

    Example:
        >>> from neurolake.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.database.connection_string)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment (useful for testing)

    Returns:
        Settings: New settings instance
    """
    global _settings
    _settings = Settings()
    return _settings


# Convenience exports
settings = get_settings()

__all__ = [
    "Settings",
    "DatabaseSettings",
    "StorageSettings",
    "RedisSettings",
    "QdrantSettings",
    "LLMSettings",
    "OpenAISettings",
    "AnthropicSettings",
    "APISettings",
    "MonitoringSettings",
    "get_settings",
    "reload_settings",
    "settings",
]
