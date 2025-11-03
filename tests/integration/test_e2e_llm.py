"""
End-to-End LLM Integration Tests

Tests the complete LLM integration including:
- Provider integration (OpenAI, Anthropic, Ollama)
- Rate limiting and retry logic
- Response caching
- Fallback mechanisms
- Usage tracking
- Factory pattern
- Integration with query generation
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Iterator

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage, MessageRole
from neurolake.llm.factory import LLMFactory, ManagedLLM
from neurolake.llm.config import LLMConfig
from neurolake.llm.cache import LLMCache
from neurolake.llm.rate_limiter import RateLimiter, MultiProviderRateLimiter
from neurolake.llm.retry import RetryHandler
from neurolake.llm.usage import UsageTracker


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(
        self,
        name: str = "mock",
        model: str = "mock-model",
        fail_count: int = 0,
        delay: float = 0.0
    ):
        self.name = name
        self.model = model
        self.fail_count = fail_count
        self.current_failures = 0
        self.delay = delay
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        *,
        system: str = None,
        messages: list = None,
        max_tokens: int = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate mock response."""
        self.call_count += 1

        # Simulate delay
        if self.delay > 0:
            time.sleep(self.delay)

        # Simulate failures
        if self.current_failures < self.fail_count:
            self.current_failures += 1
            raise RuntimeError(f"{self.name} temporary failure")

        return LLMResponse(
            text=f"Mock response from {self.name} to: {prompt[:50]}...",
            provider=self.name,
            model=self.model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=10,
            total_tokens=len(prompt.split()) + 10,
            cost=0.001,
            latency_ms=self.delay * 1000 if self.delay > 0 else 10.0
        )

    def stream(
        self,
        prompt: str,
        **kwargs
    ) -> Iterator[str]:
        """Stream mock response."""
        response = self.generate(prompt, **kwargs)
        words = response.text.split()
        for word in words:
            yield word + " "

    def count_tokens(self, text: str) -> int:
        """Count tokens (mock: word count)."""
        return len(text.split())

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model

    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.name


@pytest.fixture
def mock_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def llm_config():
    """Create test LLM config."""
    return LLMConfig(
        openai_api_key="sk-test-key",
        anthropic_api_key="sk-ant-test-key",
        enable_cache=True,
        cache_ttl=300,
        max_retries=3,
        retry_delay=0.1
    )


class TestLLMCache:
    """Test LLM response caching."""

    def test_cache_hit_and_miss(self):
        """Test cache hit and miss behavior."""
        cache = LLMCache(ttl=300)

        # Generate key
        key = cache.generate_key(
            prompt="What is a data lake?",
            model="gpt-4",
            temperature=0.7
        )

        # Miss
        result = cache.get(key)
        assert result is None
        assert cache.misses == 1
        assert cache.hits == 0

        # Set
        response = {"text": "A data lake is...", "cost": 0.01}
        cache.set(key, response)

        # Hit
        result = cache.get(key)
        assert result is not None
        assert result["text"] == "A data lake is..."
        assert cache.hits == 1
        assert cache.misses == 1

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = LLMCache(ttl=1)  # 1 second TTL

        key = cache.generate_key("test", "gpt-4")
        cache.set(key, {"text": "response"})

        # Should hit immediately
        assert cache.get(key) is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should miss after expiration
        assert cache.get(key) is None

    def test_cache_max_size_eviction(self):
        """Test LRU eviction when max size reached."""
        cache = LLMCache(ttl=300, max_size=3)

        # Fill cache
        for i in range(3):
            key = cache.generate_key(f"prompt-{i}", "gpt-4")
            cache.set(key, {"text": f"response-{i}"})

        assert len(cache.cache) == 3

        # Add one more (should evict LRU)
        key4 = cache.generate_key("prompt-4", "gpt-4")
        cache.set(key4, {"text": "response-4"})

        assert len(cache.cache) == 3  # Still 3 (one evicted)

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = LLMCache(ttl=300)

        key1 = cache.generate_key("prompt1", "gpt-4")
        key2 = cache.generate_key("prompt2", "gpt-4")

        # Misses
        cache.get(key1)
        cache.get(key2)

        # Set and hit
        cache.set(key1, {"text": "response1"})
        cache.get(key1)
        cache.get(key1)

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["total_requests"] == 4
        assert stats["hit_rate"] == 50.0
        assert stats["size"] == 1

    def test_cache_key_consistency(self):
        """Test cache key generation is consistent."""
        cache = LLMCache()

        # Same parameters should generate same key
        key1 = cache.generate_key("test", "gpt-4", temperature=0.7)
        key2 = cache.generate_key("test", "gpt-4", temperature=0.7)
        assert key1 == key2

        # Different parameters should generate different keys
        key3 = cache.generate_key("test", "gpt-4", temperature=0.8)
        assert key1 != key3

        key4 = cache.generate_key("different", "gpt-4", temperature=0.7)
        assert key1 != key4


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)

        # Should allow burst immediately
        for _ in range(5):
            assert limiter.acquire(blocking=False) is True

        # Should be depleted
        assert limiter.acquire(blocking=False) is False

    def test_rate_limiter_refill(self):
        """Test token bucket refill."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=2)

        # Deplete
        limiter.acquire()
        limiter.acquire()
        assert limiter.acquire(blocking=False) is False

        # Wait for refill (60 req/min = 1 req/sec)
        time.sleep(1.1)

        # Should have refilled
        assert limiter.acquire(blocking=False) is True

    def test_rate_limiter_wait_time(self):
        """Test wait time calculation."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)

        # Deplete
        limiter.acquire()

        # Check wait time
        wait_time = limiter.get_wait_time(tokens=1)
        assert wait_time > 0
        assert wait_time <= 1.0  # 60 req/min = 1 req/sec

    def test_multi_provider_rate_limiter(self):
        """Test multi-provider rate limiting."""
        limiter = MultiProviderRateLimiter()
        limiter.set_limit("openai", requests_per_minute=60, burst_size=5)
        limiter.set_limit("anthropic", requests_per_minute=50, burst_size=3)

        # OpenAI should allow 5
        for _ in range(5):
            assert limiter.acquire("openai", blocking=False) is True

        # Anthropic should allow 3
        for _ in range(3):
            assert limiter.acquire("anthropic", blocking=False) is True

        # Both should be depleted
        assert limiter.acquire("openai", blocking=False) is False
        assert limiter.acquire("anthropic", blocking=False) is False

        # Unknown provider should be allowed
        assert limiter.acquire("unknown", blocking=False) is True


class TestRetryLogic:
    """Test retry handler functionality."""

    def test_retry_handler_success(self):
        """Test successful execution without retries."""
        handler = RetryHandler(max_retries=3)
        mock_func = Mock(return_value="success")

        result = handler.execute(mock_func, "arg1", kwarg1="val1")

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_handler_with_retries(self):
        """Test retry on failure."""
        handler = RetryHandler(max_retries=3, initial_delay=0.01)

        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            RuntimeError("fail 1"),
            RuntimeError("fail 2"),
            "success"
        ])

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_handler_max_retries_exceeded(self):
        """Test max retries exceeded."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)

        # Always fail
        mock_func = Mock(side_effect=RuntimeError("always fails"))

        with pytest.raises(RuntimeError, match="always fails"):
            handler.execute(mock_func)

        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_retry_handler_exponential_backoff(self):
        """Test exponential backoff timing."""
        handler = RetryHandler(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0
        )

        mock_func = Mock(side_effect=[
            RuntimeError("fail 1"),
            RuntimeError("fail 2"),
            "success"
        ])

        start = time.time()
        result = handler.execute(mock_func)
        elapsed = time.time() - start

        # Should have delays of ~0.1 and ~0.2 seconds
        assert elapsed >= 0.3  # Total delay
        assert result == "success"


class TestLLMProviderBasic:
    """Test basic LLM provider functionality."""

    def test_mock_provider_generation(self, mock_provider):
        """Test basic generation with mock provider."""
        response = mock_provider.generate("What is a data lake?")

        assert response.text is not None
        assert "Mock response" in response.text
        assert response.provider == "mock"
        assert response.model == "mock-model"
        assert response.prompt_tokens > 0
        assert response.completion_tokens > 0
        assert response.total_tokens > 0
        assert response.cost > 0

    def test_mock_provider_streaming(self, mock_provider):
        """Test streaming with mock provider."""
        chunks = list(mock_provider.stream("Test prompt"))

        assert len(chunks) > 0
        full_text = "".join(chunks)
        assert "Mock response" in full_text

    def test_provider_token_counting(self, mock_provider):
        """Test token counting."""
        text = "This is a test sentence with multiple words"
        tokens = mock_provider.count_tokens(text)

        assert tokens == 8  # Word count

    def test_provider_with_delay(self):
        """Test provider with simulated latency."""
        provider = MockLLMProvider(delay=0.1)

        start = time.time()
        response = provider.generate("test")
        elapsed = time.time() - start

        assert elapsed >= 0.1
        assert response.latency_ms >= 100


class TestLLMFactory:
    """Test LLM factory pattern."""

    @patch("neurolake.llm.factory.OpenAIProvider")
    def test_factory_create_openai(self, mock_openai, llm_config):
        """Test creating OpenAI provider."""
        mock_instance = Mock()
        mock_openai.return_value = mock_instance

        provider = LLMFactory.create(
            "openai",
            api_key="sk-test",
            model="gpt-4",
            config=llm_config
        )

        assert mock_openai.called

    @patch("neurolake.llm.factory.AnthropicProvider")
    def test_factory_create_anthropic(self, mock_anthropic, llm_config):
        """Test creating Anthropic provider."""
        mock_instance = Mock()
        mock_anthropic.return_value = mock_instance

        provider = LLMFactory.create(
            "anthropic",
            api_key="sk-ant-test",
            config=llm_config
        )

        assert mock_anthropic.called

    @patch("neurolake.llm.factory.OllamaProvider")
    def test_factory_create_ollama(self, mock_ollama, llm_config):
        """Test creating Ollama provider."""
        mock_instance = Mock()
        mock_ollama.return_value = mock_instance

        provider = LLMFactory.create(
            "ollama",
            model="llama2",
            config=llm_config
        )

        assert mock_ollama.called

    def test_factory_invalid_provider(self, llm_config):
        """Test creating invalid provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMFactory.create("invalid", config=llm_config)

    def test_factory_missing_api_key(self):
        """Test missing API key."""
        config = LLMConfig()  # No API keys

        with pytest.raises(ValueError, match="API key required"):
            LLMFactory.create("openai", config=config)


class TestManagedLLM:
    """Test managed LLM with fallbacks."""

    def test_managed_llm_primary_success(self, llm_config):
        """Test successful request to primary provider."""
        # Mock the factory to return our mock provider
        mock_primary = MockLLMProvider("openai")

        with patch.object(LLMFactory, "create", return_value=mock_primary):
            llm = ManagedLLM(
                primary="openai",
                fallbacks=[],
                config=llm_config
            )

            response = llm.generate("What is NeuroLake?")

            assert response is not None
            assert "Mock response" in response.text
            assert mock_primary.call_count == 1

    def test_managed_llm_fallback_on_failure(self, llm_config):
        """Test fallback when primary fails."""
        # Primary fails, fallback succeeds
        mock_primary = MockLLMProvider("openai", fail_count=999)
        mock_fallback = MockLLMProvider("anthropic")

        def create_provider(provider, **kwargs):
            if provider == "openai":
                return mock_primary
            elif provider == "anthropic":
                return mock_fallback
            raise ValueError(f"Unknown provider: {provider}")

        with patch.object(LLMFactory, "create", side_effect=create_provider):
            llm = ManagedLLM(
                primary="openai",
                fallbacks=["anthropic"],
                config=llm_config
            )

            response = llm.generate("What is NeuroLake?")

            assert response is not None
            assert response.provider == "anthropic"
            assert mock_fallback.call_count == 1

    def test_managed_llm_all_providers_fail(self, llm_config):
        """Test all providers failing."""
        mock_primary = MockLLMProvider("openai", fail_count=999)
        mock_fallback = MockLLMProvider("anthropic", fail_count=999)

        def create_provider(provider, **kwargs):
            if provider == "openai":
                return mock_primary
            elif provider == "anthropic":
                return mock_fallback
            raise ValueError(f"Unknown provider: {provider}")

        with patch.object(LLMFactory, "create", side_effect=create_provider):
            llm = ManagedLLM(
                primary="openai",
                fallbacks=["anthropic"],
                config=llm_config
            )

            with pytest.raises(RuntimeError, match="All providers failed"):
                llm.generate("What is NeuroLake?")

    def test_managed_llm_with_caching(self, llm_config):
        """Test caching in managed LLM."""
        mock_primary = MockLLMProvider("openai")

        with patch.object(LLMFactory, "create", return_value=mock_primary):
            llm = ManagedLLM(
                primary="openai",
                config=llm_config
            )

            # First call - cache miss
            response1 = llm.generate("What is NeuroLake?")
            assert not response1.cached
            assert mock_primary.call_count == 1

            # Second call - cache hit
            response2 = llm.generate("What is NeuroLake?")
            assert response2.cached
            assert mock_primary.call_count == 1  # No additional call

    def test_managed_llm_statistics(self, llm_config):
        """Test usage and cache statistics."""
        mock_primary = MockLLMProvider("openai")

        with patch.object(LLMFactory, "create", return_value=mock_primary):
            llm = ManagedLLM(
                primary="openai",
                config=llm_config
            )

            # Make some requests
            llm.generate("Query 1")
            llm.generate("Query 2")
            llm.generate("Query 1")  # Cache hit

            stats = llm.get_stats()

            assert "usage" in stats
            assert "cache" in stats
            assert stats["cache"]["hits"] == 1
            assert stats["cache"]["misses"] == 2


class TestUsageTracking:
    """Test usage tracking functionality."""

    def test_usage_tracker_basic(self):
        """Test basic usage tracking."""
        tracker = UsageTracker()

        tracker.record(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50
        )

        tracker.record(
            provider="openai",
            model="gpt-4",
            prompt_tokens=200,
            completion_tokens=100
        )

        stats = tracker.get_stats()
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 450  # 100+50+200+100
        assert stats["total_cost"] > 0  # Cost is calculated based on pricing

    def test_usage_tracker_by_provider(self):
        """Test usage tracking per provider."""
        tracker = UsageTracker()

        tracker.record("openai", "gpt-4", 100, 50)
        tracker.record("anthropic", "claude-3-sonnet-20240229", 150, 75)
        tracker.record("openai", "gpt-4", 100, 50)

        stats = tracker.get_stats()

        # Check provider breakdown
        assert "by_provider" in stats
        assert "openai" in stats["by_provider"]
        assert "anthropic" in stats["by_provider"]
        assert stats["by_provider"]["openai"]["requests"] == 2
        assert stats["by_provider"]["anthropic"]["requests"] == 1


class TestLLMIntegration:
    """Test end-to-end LLM integration scenarios."""

    def test_complete_llm_pipeline_with_retry_and_cache(self, llm_config):
        """Test complete pipeline: retry -> cache -> fallback."""
        # Primary fails once, then succeeds
        mock_primary = MockLLMProvider("openai", fail_count=1)

        with patch.object(LLMFactory, "create", return_value=mock_primary):
            llm = ManagedLLM(
                primary="openai",
                config=llm_config
            )

            # First request - will retry once
            response1 = llm.generate("Test query")
            assert response1 is not None
            assert mock_primary.call_count == 2  # Failed once, then succeeded

            # Second request - cache hit
            mock_primary.call_count = 0  # Reset counter
            response2 = llm.generate("Test query")
            assert response2.cached
            assert mock_primary.call_count == 0  # No new calls

    def test_rate_limited_requests(self, llm_config):
        """Test rate limiting in action."""
        mock_primary = MockLLMProvider("openai")

        # Set very low rate limit for testing
        llm_config.openai_rpm = 2

        with patch.object(LLMFactory, "create", return_value=mock_primary):
            llm = ManagedLLM(
                primary="openai",
                config=llm_config
            )

            # Burst should work
            start = time.time()
            for i in range(2):
                llm.generate(f"Query {i}", use_cache=False)
            elapsed = time.time() - start

            # Should be fast (within burst)
            assert elapsed < 1.0

    def test_provider_response_parsing(self, mock_provider):
        """Test parsing provider responses."""
        response = mock_provider.generate(
            "Explain data lakes",
            max_tokens=100,
            temperature=0.5
        )

        assert isinstance(response, LLMResponse)
        assert response.text != ""
        assert response.provider == "mock"
        assert response.model == "mock-model"
        assert response.prompt_tokens > 0
        assert response.completion_tokens > 0
        assert response.cost >= 0
        assert response.latency_ms >= 0

    def test_llm_with_conversation_history(self, mock_provider):
        """Test LLM with conversation context."""
        messages = [
            LLMMessage(role=MessageRole.USER, content="What is NeuroLake?"),
            LLMMessage(role=MessageRole.ASSISTANT, content="NeuroLake is a data platform..."),
            LLMMessage(role=MessageRole.USER, content="How does it work?")
        ]

        response = mock_provider.generate(
            "Follow-up question",
            messages=messages
        )

        assert response is not None
        assert response.text != ""


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_provider_connection_error(self):
        """Test handling connection errors."""
        provider = MockLLMProvider(fail_count=999)

        with pytest.raises(RuntimeError, match="temporary failure"):
            provider.generate("test")

    def test_invalid_api_key_error(self):
        """Test handling invalid API key."""
        config = LLMConfig()  # No API key

        with pytest.raises(ValueError, match="API key required"):
            LLMFactory.create("openai", config=config)

    def test_timeout_error_handling(self):
        """Test handling timeout errors."""
        # Provider with long delay
        provider = MockLLMProvider(delay=2.0)

        # This should complete but take time
        start = time.time()
        response = provider.generate("test")
        elapsed = time.time() - start

        assert elapsed >= 2.0
        assert response is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
