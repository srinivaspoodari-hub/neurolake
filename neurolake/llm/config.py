"""
LLM Configuration

Manages API keys, rate limits, and provider settings.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    # API Keys (read from environment if not provided)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # Model defaults
    openai_model: str = "gpt-4"
    anthropic_model: str = "claude-3-sonnet-20240229"
    ollama_model: str = "llama2"

    # Rate limiting (requests per minute)
    openai_rpm: int = 60
    anthropic_rpm: int = 50
    ollama_rpm: int = 1000

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0

    # Caching
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour

    # Cost tracking
    track_usage: bool = True

    # Timeouts
    timeout: float = 60.0

    # Additional settings
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if self.anthropic_api_key is None:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if ollama_url := os.getenv("OLLAMA_BASE_URL"):
            self.ollama_base_url = ollama_url

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        if provider == "openai":
            return self.openai_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key
        return None

    def get_model(self, provider: str) -> str:
        """Get default model for a provider."""
        if provider == "openai":
            return self.openai_model
        elif provider == "anthropic":
            return self.anthropic_model
        elif provider == "ollama":
            return self.ollama_model
        raise ValueError(f"Unknown provider: {provider}")

    def get_rpm(self, provider: str) -> int:
        """Get rate limit for a provider."""
        if provider == "openai":
            return self.openai_rpm
        elif provider == "anthropic":
            return self.anthropic_rpm
        elif provider == "ollama":
            return self.ollama_rpm
        return 60


__all__ = ["LLMConfig"]
