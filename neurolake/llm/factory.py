"""
LLM Factory

Create and manage LLM providers with rate limiting, retries, caching, and fallbacks.
"""

from typing import Optional, List, Union
import logging

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage
from neurolake.llm.providers.openai_provider import OpenAIProvider
from neurolake.llm.providers.anthropic_provider import AnthropicProvider
from neurolake.llm.providers.ollama_provider import OllamaProvider
from neurolake.llm.config import LLMConfig
from neurolake.llm.usage import UsageTracker
from neurolake.llm.cache import LLMCache
from neurolake.llm.rate_limiter import MultiProviderRateLimiter
from neurolake.llm.retry import RetryHandler

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating and managing LLM providers.

    Example:
        # Create provider
        llm = LLMFactory.create("openai", api_key="sk-...")

        # With config
        config = LLMConfig(
            openai_api_key="sk-...",
            enable_cache=True
        )
        llm = LLMFactory.create("openai", config=config)
    """

    @staticmethod
    def create(
        provider: str,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        usage_tracker: Optional[UsageTracker] = None
    ) -> Union[OpenAIProvider, AnthropicProvider, OllamaProvider]:
        """
        Create an LLM provider.

        Args:
            provider: Provider name (openai, anthropic, ollama)
            api_key: Optional API key
            model: Optional model override
            config: Optional configuration
            usage_tracker: Optional usage tracker

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is unknown or missing API key
        """
        config = config or LLMConfig()
        tracker = usage_tracker or UsageTracker()

        if provider == "openai":
            key = api_key or config.get_api_key("openai")
            if not key:
                raise ValueError("OpenAI API key required")

            mdl = model or config.get_model("openai")

            return OpenAIProvider(
                api_key=key,
                model=mdl,
                usage_tracker=tracker
            )

        elif provider == "anthropic":
            key = api_key or config.get_api_key("anthropic")
            if not key:
                raise ValueError("Anthropic API key required")

            mdl = model or config.get_model("anthropic")

            return AnthropicProvider(
                api_key=key,
                model=mdl,
                usage_tracker=tracker
            )

        elif provider == "ollama":
            mdl = model or config.get_model("ollama")

            return OllamaProvider(
                base_url=config.ollama_base_url,
                model=mdl,
                usage_tracker=tracker
            )

        else:
            raise ValueError(
                f"Unknown provider: {provider}. "
                "Supported: openai, anthropic, ollama"
            )


class ManagedLLM:
    """
    Managed LLM with rate limiting, retries, caching, and fallbacks.

    Example:
        llm = ManagedLLM(
            primary="openai",
            fallbacks=["anthropic", "ollama"],
            config=config
        )

        # Generate with automatic fallbacks
        response = llm.generate("Explain data lakes")
    """

    def __init__(
        self,
        primary: str,
        *,
        fallbacks: Optional[List[str]] = None,
        config: Optional[LLMConfig] = None,
        usage_tracker: Optional[UsageTracker] = None
    ):
        """
        Initialize managed LLM.

        Args:
            primary: Primary provider
            fallbacks: List of fallback providers
            config: Optional configuration
            usage_tracker: Optional usage tracker
        """
        self.config = config or LLMConfig()
        self.usage_tracker = usage_tracker or UsageTracker()

        # Create providers
        self.primary_name = primary
        self.fallback_names = fallbacks or []

        self.primary = LLMFactory.create(
            primary,
            config=self.config,
            usage_tracker=self.usage_tracker
        )

        self.fallbacks = [
            LLMFactory.create(
                provider,
                config=self.config,
                usage_tracker=self.usage_tracker
            )
            for provider in self.fallback_names
        ]

        # Setup rate limiter
        self.rate_limiter = MultiProviderRateLimiter()
        self.rate_limiter.set_limit(
            "openai",
            self.config.get_rpm("openai")
        )
        self.rate_limiter.set_limit(
            "anthropic",
            self.config.get_rpm("anthropic")
        )
        self.rate_limiter.set_limit(
            "ollama",
            self.config.get_rpm("ollama")
        )

        # Setup cache
        self.cache = LLMCache(ttl=self.config.cache_ttl) if self.config.enable_cache else None

        # Setup retry handler
        self.retry_handler = RetryHandler(
            max_retries=self.config.max_retries,
            initial_delay=self.config.retry_delay,
            backoff_factor=self.config.backoff_factor
        )

    def generate(
        self,
        prompt: str,
        *,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with fallbacks.

        Args:
            prompt: The prompt
            use_cache: Whether to use cache
            **kwargs: Additional parameters

        Returns:
            LLMResponse
        """
        # Check cache
        if use_cache and self.cache:
            cache_key = self.cache.generate_key(
                prompt=prompt,
                model=self.primary.get_model_name(),
                **kwargs
            )

            if cached := self.cache.get(cache_key):
                cached["cached"] = True
                return LLMResponse(**cached)

        # Try primary provider
        providers = [(self.primary_name, self.primary)] + [
            (name, provider) for name, provider in zip(self.fallback_names, self.fallbacks)
        ]

        last_error = None
        attempted_providers = []

        for idx, (provider_name, provider) in enumerate(providers):
            attempted_providers.append(provider_name)

            # Log which provider we're trying
            if idx == 0:
                logger.info(f"Attempting primary provider: {provider_name}")
            else:
                logger.info(
                    f"Fallback {idx}/{len(providers)-1}: Trying {provider_name} "
                    f"(previous providers failed)"
                )

            try:
                # Rate limit
                self.rate_limiter.acquire(provider_name)

                # Generate with retry
                response = self.retry_handler.execute(
                    provider.generate,
                    prompt,
                    **kwargs
                )

                # Log success
                logger.info(
                    f"✓ Success with {provider_name} "
                    f"(cost: ${response.cost:.4f}, latency: {response.latency_ms:.0f}ms)"
                )

                # Cache response
                if use_cache and self.cache:
                    response_dict = {
                        "text": response.text,
                        "provider": response.provider,
                        "model": response.model,
                        "prompt_tokens": response.prompt_tokens,
                        "completion_tokens": response.completion_tokens,
                        "total_tokens": response.total_tokens,
                        "cost": response.cost,
                        "latency_ms": response.latency_ms,
                        "finish_reason": response.finish_reason
                    }
                    self.cache.set(cache_key, response_dict)

                return response

            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                if idx < len(providers) - 1:
                    logger.warning(
                        f"✗ {provider_name} failed with {error_type}: {e}. "
                        f"Falling back to next provider..."
                    )
                else:
                    logger.error(
                        f"✗ {provider_name} failed with {error_type}: {e}. "
                        f"No more fallbacks available."
                    )
                continue

        # All providers failed
        raise RuntimeError(
            f"All providers failed after trying: {', '.join(attempted_providers)}. "
            f"Last error ({type(last_error).__name__}): {last_error}"
        )

    def get_stats(self):
        """Get statistics."""
        stats = {
            "usage": self.usage_tracker.get_stats(),
        }

        if self.cache:
            stats["cache"] = self.cache.get_stats()

        return stats


__all__ = ["LLMFactory", "ManagedLLM"]
