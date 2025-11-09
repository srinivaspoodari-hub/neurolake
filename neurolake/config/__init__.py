"""
NeuroLake Configuration Module

Provides centralized configuration management using Pydantic Settings.
All settings can be configured via environment variables with NEUROLAKE_ prefix.

Example:
    from neurolake.config import get_settings

    settings = get_settings()
    print(settings.database.connection_string)
"""

from neurolake.config.settings import (
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
    settings,
)

from neurolake.config.environment import (
    EnvironmentManager,
    Environment,
    CloudProvider,
    Permission,
    EnvironmentConfig,
    get_environment_manager,
)

__all__ = [
    # Settings
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
    # Environment
    "EnvironmentManager",
    "Environment",
    "CloudProvider",
    "Permission",
    "EnvironmentConfig",
    "get_environment_manager",
]
