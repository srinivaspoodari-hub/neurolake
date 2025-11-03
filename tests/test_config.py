"""
Comprehensive tests for NeuroLake configuration module.

Tests all settings classes, validators, computed fields, and environment variable handling.
"""

import pytest
import os
from pathlib import Path
from pydantic import ValidationError
from neurolake.config import (
    Settings,
    DatabaseSettings,
    StorageSettings,
    RedisSettings,
    QdrantSettings,
    LLMSettings,
    OpenAISettings,
    AnthropicSettings,
    APISettings,
    MonitoringSettings,
    get_settings,
    reload_settings,
)


# =============================================================================
# DatabaseSettings Tests
# =============================================================================

class TestDatabaseSettings:
    """Test DatabaseSettings configuration"""

    def test_default_values(self):
        """Test default database settings"""
        db = DatabaseSettings()
        assert db.host == "localhost"
        assert db.port == 5432
        assert db.database == "neurolake"
        assert db.username == "neurolake"
        assert db.pool_size == 20
        assert db.max_overflow == 10
        assert db.sslmode == "prefer"

    def test_connection_string(self):
        """Test connection string generation"""
        db = DatabaseSettings(
            host="db.example.com",
            port=5433,
            database="mydb",
            username="user",
            password="pass123"
        )
        expected = "postgresql://user:pass123@db.example.com:5433/mydb"
        assert db.connection_string == expected

    def test_async_connection_string(self):
        """Test async connection string generation"""
        db = DatabaseSettings(
            host="db.example.com",
            port=5433,
            database="mydb",
            username="user",
            password="pass123"
        )
        expected = "postgresql+asyncpg://user:pass123@db.example.com:5433/mydb"
        assert db.async_connection_string == expected

    def test_port_validation(self):
        """Test port range validation"""
        # Valid ports
        DatabaseSettings(port=1)
        DatabaseSettings(port=65535)

        # Invalid ports
        with pytest.raises(ValidationError):
            DatabaseSettings(port=0)
        with pytest.raises(ValidationError):
            DatabaseSettings(port=65536)

    def test_pool_size_validation(self):
        """Test pool size validation"""
        # Valid pool sizes
        DatabaseSettings(pool_size=1)
        DatabaseSettings(pool_size=100)

        # Invalid pool sizes
        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=0)
        with pytest.raises(ValidationError):
            DatabaseSettings(pool_size=101)

    def test_env_variable_loading(self, monkeypatch):
        """Test loading from environment variables"""
        monkeypatch.setenv("NEUROLAKE_DATABASE_HOST", "prod-db.example.com")
        monkeypatch.setenv("NEUROLAKE_DATABASE_PORT", "5433")
        monkeypatch.setenv("NEUROLAKE_DATABASE_DATABASE", "production")
        monkeypatch.setenv("NEUROLAKE_DATABASE_USERNAME", "prod_user")
        monkeypatch.setenv("NEUROLAKE_DATABASE_POOL_SIZE", "50")

        db = DatabaseSettings()
        assert db.host == "prod-db.example.com"
        assert db.port == 5433
        assert db.database == "production"
        assert db.username == "prod_user"
        assert db.pool_size == 50

    def test_ssl_settings(self):
        """Test SSL configuration"""
        db = DatabaseSettings(
            sslmode="require",
            sslcert="/path/to/cert.pem",
            sslkey="/path/to/key.pem"
        )
        assert db.sslmode == "require"
        assert db.sslcert == "/path/to/cert.pem"
        assert db.sslkey == "/path/to/key.pem"


# =============================================================================
# StorageSettings Tests
# =============================================================================

class TestStorageSettings:
    """Test StorageSettings configuration"""

    def test_default_values(self):
        """Test default storage settings"""
        storage = StorageSettings()
        assert storage.endpoint == "localhost:9000"
        assert storage.access_key == "neurolake"
        assert storage.secure is False
        assert storage.region == "us-east-1"
        assert storage.data_bucket == "data"
        assert storage.temp_bucket == "temp"

    def test_endpoint_validation_strips_protocol(self):
        """Test endpoint validator strips http/https"""
        storage = StorageSettings(endpoint="http://localhost:9000")
        assert storage.endpoint == "localhost:9000"

        storage = StorageSettings(endpoint="https://s3.amazonaws.com")
        assert storage.endpoint == "s3.amazonaws.com"

    def test_multipart_threshold_validation(self):
        """Test multipart threshold minimum"""
        # Valid threshold (>= 5MB)
        StorageSettings(multipart_threshold=5 * 1024 * 1024)

        # Invalid threshold (< 5MB)
        with pytest.raises(ValidationError):
            StorageSettings(multipart_threshold=4 * 1024 * 1024)

    def test_max_concurrency_validation(self):
        """Test max concurrency validation"""
        # Valid
        StorageSettings(max_concurrency=1)
        StorageSettings(max_concurrency=50)

        # Invalid
        with pytest.raises(ValidationError):
            StorageSettings(max_concurrency=0)
        with pytest.raises(ValidationError):
            StorageSettings(max_concurrency=51)

    def test_bucket_configuration(self):
        """Test custom bucket names"""
        storage = StorageSettings(
            data_bucket="my-data",
            temp_bucket="my-temp",
            archive_bucket="my-archive"
        )
        assert storage.data_bucket == "my-data"
        assert storage.temp_bucket == "my-temp"
        assert storage.archive_bucket == "my-archive"


# =============================================================================
# RedisSettings Tests
# =============================================================================

class TestRedisSettings:
    """Test RedisSettings configuration"""

    def test_default_values(self):
        """Test default Redis settings"""
        redis = RedisSettings()
        assert redis.host == "localhost"
        assert redis.port == 6379
        assert redis.db == 0
        assert redis.max_connections == 50
        assert redis.default_ttl == 3600
        assert redis.decode_responses is True

    def test_db_validation(self):
        """Test Redis DB number validation"""
        # Valid
        RedisSettings(db=0)
        RedisSettings(db=15)

        # Invalid
        with pytest.raises(ValidationError):
            RedisSettings(db=-1)
        with pytest.raises(ValidationError):
            RedisSettings(db=16)

    def test_ttl_settings(self):
        """Test TTL configuration"""
        redis = RedisSettings(
            default_ttl=1800,
            query_result_ttl=900,
            metadata_ttl=3600
        )
        assert redis.default_ttl == 1800
        assert redis.query_result_ttl == 900
        assert redis.metadata_ttl == 3600

    def test_ttl_minimum_validation(self):
        """Test TTL minimum values"""
        # Valid (>= 60)
        RedisSettings(default_ttl=60)

        # Invalid (< 60)
        with pytest.raises(ValidationError):
            RedisSettings(default_ttl=59)

    def test_password_optional(self):
        """Test password is optional"""
        redis = RedisSettings()
        assert redis.password is None

        redis = RedisSettings(password="secret")
        assert redis.password == "secret"


# =============================================================================
# QdrantSettings Tests
# =============================================================================

class TestQdrantSettings:
    """Test QdrantSettings configuration"""

    def test_default_values(self):
        """Test default Qdrant settings"""
        qdrant = QdrantSettings()
        assert qdrant.host == "localhost"
        assert qdrant.port == 6333
        assert qdrant.grpc_port == 6334
        assert qdrant.embeddings_collection == "neurolake_embeddings"
        assert qdrant.vector_size == 1536
        assert qdrant.prefer_grpc is True

    def test_vector_size_validation(self):
        """Test vector size minimum"""
        # Valid (>= 128)
        QdrantSettings(vector_size=128)
        QdrantSettings(vector_size=1536)

        # Invalid (< 128)
        with pytest.raises(ValidationError):
            QdrantSettings(vector_size=127)

    def test_api_key_optional(self):
        """Test API key is optional"""
        qdrant = QdrantSettings()
        assert qdrant.api_key is None

        qdrant = QdrantSettings(api_key="secret-key")
        assert qdrant.api_key == "secret-key"


# =============================================================================
# LLM Settings Tests
# =============================================================================

class TestOpenAISettings:
    """Test OpenAISettings configuration"""

    def test_default_values(self):
        """Test default OpenAI settings"""
        openai = OpenAISettings()
        assert openai.model == "gpt-4-turbo-preview"
        assert openai.embedding_model == "text-embedding-3-large"
        assert openai.temperature == 0.7
        assert openai.max_tokens == 4096
        assert openai.api_key is None

    def test_temperature_validation(self):
        """Test temperature range validation"""
        # Valid
        OpenAISettings(temperature=0.0)
        OpenAISettings(temperature=2.0)

        # Invalid
        with pytest.raises(ValidationError):
            OpenAISettings(temperature=-0.1)
        with pytest.raises(ValidationError):
            OpenAISettings(temperature=2.1)

    def test_max_tokens_validation(self):
        """Test max tokens validation"""
        # Valid
        OpenAISettings(max_tokens=1)
        OpenAISettings(max_tokens=128000)

        # Invalid
        with pytest.raises(ValidationError):
            OpenAISettings(max_tokens=0)
        with pytest.raises(ValidationError):
            OpenAISettings(max_tokens=128001)


class TestAnthropicSettings:
    """Test AnthropicSettings configuration"""

    def test_default_values(self):
        """Test default Anthropic settings"""
        anthropic = AnthropicSettings()
        assert anthropic.model == "claude-3-5-sonnet-20241022"
        assert anthropic.temperature == 0.7
        assert anthropic.max_tokens == 4096
        assert anthropic.api_key is None

    def test_temperature_validation(self):
        """Test temperature range validation"""
        # Valid
        AnthropicSettings(temperature=0.0)
        AnthropicSettings(temperature=1.0)

        # Invalid
        with pytest.raises(ValidationError):
            AnthropicSettings(temperature=-0.1)
        with pytest.raises(ValidationError):
            AnthropicSettings(temperature=1.1)


class TestLLMSettings:
    """Test LLMSettings configuration"""

    def test_default_values(self):
        """Test default LLM settings"""
        llm = LLMSettings()
        assert llm.default_provider == "openai"
        assert llm.max_requests_per_minute == 50
        assert llm.max_concurrent_requests == 5
        assert isinstance(llm.openai, OpenAISettings)
        assert isinstance(llm.anthropic, AnthropicSettings)

    def test_provider_validation(self):
        """Test provider name validation"""
        # Valid
        LLMSettings(default_provider="openai")
        LLMSettings(default_provider="anthropic")
        LLMSettings(default_provider="OPENAI")  # Case insensitive

        # Invalid
        with pytest.raises(ValidationError):
            LLMSettings(default_provider="invalid")

    def test_nested_settings(self):
        """Test nested OpenAI and Anthropic settings"""
        llm = LLMSettings()
        assert llm.openai.model == "gpt-4-turbo-preview"
        assert llm.anthropic.model == "claude-3-5-sonnet-20241022"


# =============================================================================
# APISettings Tests
# =============================================================================

class TestAPISettings:
    """Test APISettings configuration"""

    def test_default_values(self):
        """Test default API settings"""
        api = APISettings()
        assert api.host == "0.0.0.0"
        assert api.port == 8000
        assert api.reload is False
        assert api.workers == 4
        assert api.cors_allow_credentials is True
        assert api.algorithm == "HS256"

    def test_port_validation(self):
        """Test port range validation"""
        # Valid
        APISettings(port=1)
        APISettings(port=65535)

        # Invalid
        with pytest.raises(ValidationError):
            APISettings(port=0)
        with pytest.raises(ValidationError):
            APISettings(port=65536)

    def test_workers_validation(self):
        """Test workers validation"""
        # Valid
        APISettings(workers=1)
        APISettings(workers=32)

        # Invalid
        with pytest.raises(ValidationError):
            APISettings(workers=0)
        with pytest.raises(ValidationError):
            APISettings(workers=33)

    def test_token_expiration_validation(self):
        """Test access token expiration validation"""
        # Valid
        APISettings(access_token_expire_minutes=5)
        APISettings(access_token_expire_minutes=1440)

        # Invalid
        with pytest.raises(ValidationError):
            APISettings(access_token_expire_minutes=4)
        with pytest.raises(ValidationError):
            APISettings(access_token_expire_minutes=1441)

    def test_cors_origins(self):
        """Test CORS origins configuration"""
        api = APISettings(cors_origins=["http://example.com", "https://app.example.com"])
        assert len(api.cors_origins) == 2
        assert "http://example.com" in api.cors_origins


# =============================================================================
# MonitoringSettings Tests
# =============================================================================

class TestMonitoringSettings:
    """Test MonitoringSettings configuration"""

    def test_default_values(self):
        """Test default monitoring settings"""
        monitoring = MonitoringSettings()
        assert monitoring.enable_metrics is True
        assert monitoring.enable_tracing is True
        assert monitoring.log_level == "INFO"
        assert monitoring.log_format == "json"
        assert monitoring.metrics_port == 9090

    def test_log_level_validation(self):
        """Test log level validation"""
        # Valid
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            MonitoringSettings(log_level=level)
            MonitoringSettings(log_level=level.lower())  # Case insensitive

        # Invalid
        with pytest.raises(ValidationError):
            MonitoringSettings(log_level="INVALID")

    def test_log_level_case_insensitive(self):
        """Test log level is converted to uppercase"""
        monitoring = MonitoringSettings(log_level="debug")
        assert monitoring.log_level == "DEBUG"

        monitoring = MonitoringSettings(log_level="InFo")
        assert monitoring.log_level == "INFO"


# =============================================================================
# Main Settings Tests
# =============================================================================

class TestSettings:
    """Test main Settings configuration"""

    def test_default_values(self):
        """Test default settings"""
        settings = Settings()
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.app_name == "NeuroLake"
        assert settings.app_version == "0.1.0"

    def test_environment_validation(self):
        """Test environment validation"""
        # Valid
        for env in ["development", "staging", "production"]:
            Settings(environment=env)
            Settings(environment=env.upper())  # Case insensitive

        # Invalid
        with pytest.raises(ValidationError):
            Settings(environment="invalid")

    def test_nested_settings(self):
        """Test nested settings initialization"""
        settings = Settings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.storage, StorageSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.qdrant, QdrantSettings)
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.api, APISettings)
        assert isinstance(settings.monitoring, MonitoringSettings)

    def test_computed_fields(self):
        """Test computed fields"""
        dev_settings = Settings(environment="development")
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False

        prod_settings = Settings(environment="production")
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True

    def test_directory_creation(self, tmp_path):
        """Test directories are created on initialization"""
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"
        logs_dir = tmp_path / "logs"

        settings = Settings(
            data_dir=data_dir,
            cache_dir=cache_dir,
            logs_dir=logs_dir
        )

        assert data_dir.exists()
        assert cache_dir.exists()
        assert logs_dir.exists()

    def test_path_fields(self, tmp_path):
        """Test Path field handling"""
        settings = Settings(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            logs_dir=tmp_path / "logs"
        )

        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.cache_dir, Path)
        assert isinstance(settings.logs_dir, Path)


# =============================================================================
# Global Settings Tests
# =============================================================================

class TestGlobalSettings:
    """Test global settings functions"""

    def test_get_settings_singleton(self):
        """Test get_settings returns singleton"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reload_settings(self, monkeypatch):
        """Test reload_settings creates new instance"""
        settings1 = get_settings()

        # Change environment variable
        monkeypatch.setenv("NEUROLAKE_ENVIRONMENT", "production")

        settings2 = reload_settings()
        assert settings2 is not settings1
        assert settings2.environment == "production"

    def test_nested_env_variables(self, monkeypatch):
        """Test nested environment variables with delimiter"""
        monkeypatch.setenv("NEUROLAKE_DATABASE__HOST", "test-db.example.com")
        monkeypatch.setenv("NEUROLAKE_DATABASE__PORT", "5433")
        monkeypatch.setenv("NEUROLAKE_LLM__OPENAI__API_KEY", "sk-test-key")
        monkeypatch.setenv("NEUROLAKE_LLM__DEFAULT_PROVIDER", "anthropic")

        settings = reload_settings()
        assert settings.database.host == "test-db.example.com"
        assert settings.database.port == 5433
        assert settings.llm.openai.api_key == "sk-test-key"
        assert settings.llm.default_provider == "anthropic"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSettingsIntegration:
    """Integration tests for settings"""

    def test_full_configuration_from_env(self, monkeypatch):
        """Test loading full configuration from environment"""
        # Set all environment variables
        env_vars = {
            "NEUROLAKE_ENVIRONMENT": "production",
            "NEUROLAKE_DEBUG": "true",
            "NEUROLAKE_DATABASE__HOST": "prod-db.example.com",
            "NEUROLAKE_DATABASE__PORT": "5433",
            "NEUROLAKE_STORAGE__ENDPOINT": "s3.amazonaws.com",
            "NEUROLAKE_STORAGE__SECURE": "true",
            "NEUROLAKE_REDIS__HOST": "redis.example.com",
            "NEUROLAKE_REDIS__PORT": "6380",
            "NEUROLAKE_LLM__DEFAULT_PROVIDER": "anthropic",
            "NEUROLAKE_API__PORT": "8080",
            "NEUROLAKE_MONITORING__LOG_LEVEL": "DEBUG",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = reload_settings()

        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.database.host == "prod-db.example.com"
        assert settings.database.port == 5433
        assert settings.storage.endpoint == "s3.amazonaws.com"
        assert settings.storage.secure is True
        assert settings.redis.host == "redis.example.com"
        assert settings.redis.port == 6380
        assert settings.llm.default_provider == "anthropic"
        assert settings.api.port == 8080
        assert settings.monitoring.log_level == "DEBUG"

    def test_partial_configuration_with_defaults(self, monkeypatch):
        """Test partial configuration uses defaults"""
        monkeypatch.setenv("NEUROLAKE_ENVIRONMENT", "staging")
        monkeypatch.setenv("NEUROLAKE_DATABASE__HOST", "staging-db")

        settings = reload_settings()

        assert settings.environment == "staging"
        assert settings.database.host == "staging-db"
        assert settings.database.port == 5432  # Default
        assert settings.redis.host == "localhost"  # Default

    def test_database_connection_strings(self):
        """Test database connection string generation"""
        settings = Settings()
        settings.database.host = "db.example.com"
        settings.database.port = 5433
        settings.database.username = "testuser"
        settings.database.password = "testpass"
        settings.database.database = "testdb"

        assert "postgresql://testuser:testpass@db.example.com:5433/testdb" == settings.database.connection_string
        assert "postgresql+asyncpg://testuser:testpass@db.example.com:5433/testdb" == settings.database.async_connection_string

    def test_settings_immutability(self):
        """Test settings can be modified after creation"""
        settings = Settings()
        original_env = settings.environment

        # Settings should be mutable
        settings.environment = "production"
        assert settings.environment == "production"
        assert settings.environment != original_env


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_cors_origins(self):
        """Test empty CORS origins list"""
        api = APISettings(cors_origins=[])
        assert api.cors_origins == []

    def test_very_long_strings(self):
        """Test handling of very long strings"""
        long_string = "a" * 10000
        db = DatabaseSettings(password=long_string)
        assert len(db.password) == 10000

    def test_special_characters_in_passwords(self):
        """Test special characters in passwords"""
        special_password = "p@$$w0rd!#%&*()[]{}|<>?/"
        db = DatabaseSettings(password=special_password)
        assert db.password == special_password

    def test_unicode_in_strings(self):
        """Test unicode characters"""
        db = DatabaseSettings(database="neurolake_测试")
        assert "测试" in db.database

    def test_whitespace_handling(self):
        """Test whitespace in strings"""
        db = DatabaseSettings(host="  localhost  ")
        # Pydantic doesn't strip by default
        assert db.host == "  localhost  "

    def test_case_sensitivity(self):
        """Test case sensitivity in validators"""
        # Environment should be case insensitive
        settings = Settings(environment="PRODUCTION")
        assert settings.environment == "production"

        # Log level should be case insensitive
        monitoring = MonitoringSettings(log_level="debug")
        assert monitoring.log_level == "DEBUG"

    def test_numeric_string_conversion(self, monkeypatch):
        """Test numeric strings are converted properly"""
        # Create a clean environment for DatabaseSettings
        # DatabaseSettings uses NEUROLAKE_DATABASE_ prefix, not NEUROLAKE_DATABASE__
        monkeypatch.setenv("NEUROLAKE_DATABASE_PORT", "5433")
        monkeypatch.setenv("NEUROLAKE_DATABASE_POOL_SIZE", "50")

        db = DatabaseSettings()
        assert db.port == 5433
        assert isinstance(db.port, int)
        assert db.pool_size == 50
        assert isinstance(db.pool_size, int)

    def test_boolean_string_conversion(self, monkeypatch):
        """Test boolean strings are converted properly"""
        monkeypatch.setenv("NEUROLAKE_DEBUG", "true")
        monkeypatch.setenv("NEUROLAKE_API__RELOAD", "1")

        settings = reload_settings()
        assert settings.debug is True
        assert settings.api.reload is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
