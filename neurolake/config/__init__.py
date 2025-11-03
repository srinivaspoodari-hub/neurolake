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
