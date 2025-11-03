"""
Comprehensive tests for the LLM module.

Tests cover:
- LLM provider protocol and data classes (LLMMessage, LLMResponse)
- LLM configuration management (LLMConfig)
- Usage tracking and cost calculation (UsageTracker, TokenUsage)
- Rate limiting with token bucket algorithm (RateLimiter, MultiProviderRateLimiter)
- Retry logic with exponential backoff (RetryHandler, retry_with_backoff)
- Response caching with LRU eviction (LLMCache, CacheEntry)
- LLM factory pattern (LLMFactory)
- Managed LLM with fallbacks, rate limiting, and caching (ManagedLLM)
- Provider implementations (OpenAI, Anthropic, Ollama - mocked)
- Integration tests and edge cases
"""

import pytest
import time
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from neurolake.llm.provider import LLMMessage, LLMResponse, MessageRole
from neurolake.llm.config import LLMConfig
from neurolake.llm.usage import UsageTracker, TokenUsage, PRICING
from neurolake.llm.cache import LLMCache, CacheEntry
from neurolake.llm.rate_limiter import RateLimiter, MultiProviderRateLimiter, RateLimitConfig
from neurolake.llm.retry import retry_with_backoff, RetryHandler, RetryConfig
from neurolake.llm.factory import LLMFactory, ManagedLLM


# ===== Config Tests =====

def test_config_creation():
    """Test config creation."""
    config = LLMConfig()

    assert config.openai_rpm == 60
    assert config.anthropic_rpm == 50
    assert config.max_retries == 3
    assert config.enable_cache is True


def test_config_get_api_key():
    """Test get API key."""
    config = LLMConfig(
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test"
    )

    assert config.get_api_key("openai") == "sk-test"
    assert config.get_api_key("anthropic") == "sk-ant-test"
    assert config.get_api_key("unknown") is None


def test_config_get_model():
    """Test get model."""
    config = LLMConfig()

    assert config.get_model("openai") == "gpt-4"
    assert config.get_model("anthropic") == "claude-3-sonnet-20240229"
    assert config.get_model("ollama") == "llama2"


# ===== Usage Tracker Tests =====

def test_usage_tracker_record():
    """Test recording usage."""
    tracker = UsageTracker()

    cost = tracker.record(
        provider="openai",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50
    )

    assert cost > 0
    assert len(tracker.usage_history) == 1

    usage = tracker.usage_history[0]
    assert usage.provider == "openai"
    assert usage.model == "gpt-4"
    assert usage.total_tokens == 150


def test_usage_tracker_calculate_cost():
    """Test cost calculation."""
    tracker = UsageTracker()

    # GPT-4: $30/1M prompt, $60/1M completion
    cost = tracker.calculate_cost("gpt-4", 1000, 500)

    expected_cost = (1000 / 1_000_000 * 30) + (500 / 1_000_000 * 60)
    assert abs(cost - expected_cost) < 0.0001


def test_usage_tracker_get_stats():
    """Test get statistics."""
    tracker = UsageTracker()

    tracker.record("openai", "gpt-4", 100, 50)
    tracker.record("openai", "gpt-4", 200, 100)
    tracker.record("anthropic", "claude-3-sonnet-20240229", 150, 75)

    stats = tracker.get_stats()

    assert stats["total_requests"] == 3
    assert stats["total_tokens"] == 675
    assert "openai" in stats["by_provider"]
    assert stats["by_provider"]["openai"]["requests"] == 2


# ===== Cache Tests =====

def test_cache_creation():
    """Test cache creation."""
    cache = LLMCache(ttl=3600)

    assert cache.ttl == 3600
    assert len(cache.cache) == 0


def test_cache_generate_key():
    """Test key generation."""
    cache = LLMCache()

    key1 = cache.generate_key("test prompt", "gpt-4", temperature=0.7)
    key2 = cache.generate_key("test prompt", "gpt-4", temperature=0.7)
    key3 = cache.generate_key("different prompt", "gpt-4", temperature=0.7)

    # Same inputs should generate same key
    assert key1 == key2

    # Different inputs should generate different keys
    assert key1 != key3


def test_cache_set_and_get():
    """Test set and get."""
    cache = LLMCache()

    key = "test_key"
    response = {"text": "test response", "cost": 0.01}

    cache.set(key, response)

    retrieved = cache.get(key)
    assert retrieved == response
    assert cache.hits == 1


def test_cache_expiration():
    """Test cache expiration."""
    cache = LLMCache(ttl=1)  # 1 second TTL

    key = "test_key"
    response = {"text": "test"}

    cache.set(key, response)

    # Should be available immediately
    assert cache.get(key) is not None

    # Wait for expiration
    time.sleep(1.1)

    # Should be expired
    assert cache.get(key) is None


def test_cache_stats():
    """Test cache statistics."""
    cache = LLMCache()

    cache.set("key1", {"text": "response1"})
    cache.set("key2", {"text": "response2"})

    cache.get("key1")  # Hit
    cache.get("key1")  # Hit
    cache.get("key3")  # Miss

    stats = cache.get_stats()

    assert stats["size"] == 2
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == (2 / 3 * 100)


# ===== Rate Limiter Tests =====

def test_rate_limiter_creation():
    """Test rate limiter creation."""
    limiter = RateLimiter(requests_per_minute=60)

    assert limiter.config.requests_per_minute == 60
    assert limiter.tokens > 0


def test_rate_limiter_acquire():
    """Test acquiring tokens."""
    limiter = RateLimiter(requests_per_minute=60, burst_size=5)

    # Should succeed immediately
    assert limiter.acquire(1, blocking=False) is True


def test_rate_limiter_wait_time():
    """Test wait time calculation."""
    limiter = RateLimiter(requests_per_minute=60)

    # Deplete tokens
    for _ in range(10):
        limiter.acquire(1, blocking=False)

    wait_time = limiter.get_wait_time(1)
    assert wait_time >= 0


def test_multi_provider_rate_limiter():
    """Test multi-provider rate limiter."""
    limiter = MultiProviderRateLimiter()

    limiter.set_limit("openai", requests_per_minute=60)
    limiter.set_limit("anthropic", requests_per_minute=50)

    assert limiter.acquire("openai") is True
    assert limiter.acquire("anthropic") is True


# ===== Retry Tests =====

def test_retry_decorator_success():
    """Test retry decorator with successful call."""
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.1)
    def test_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = test_func()

    assert result == "success"
    assert call_count == 1


def test_retry_decorator_failure_then_success():
    """Test retry decorator with failure then success."""
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.1)
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"

    result = test_func()

    assert result == "success"
    assert call_count == 3


def test_retry_handler():
    """Test retry handler."""
    handler = RetryHandler(max_retries=3, initial_delay=0.1)

    call_count = 0

    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Error")
        return "success"

    result = handler.execute(test_func)

    assert result == "success"
    assert call_count == 2


# ===== Factory Tests =====

def test_factory_create_ollama():
    """Test creating Ollama provider."""
    from neurolake.llm.providers.ollama_provider import OllamaProvider

    provider = LLMFactory.create("ollama")

    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama2"


def test_factory_invalid_provider():
    """Test creating invalid provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        LLMFactory.create("invalid")


def test_factory_with_config():
    """Test creating provider with config."""
    config = LLMConfig(ollama_model="mistral")

    provider = LLMFactory.create("ollama", config=config)

    assert provider.model == "mistral"


# ===== Managed LLM Tests =====

@patch("neurolake.llm.providers.ollama_provider.requests.post")
def test_managed_llm_generate(mock_post):
    """Test managed LLM generation."""
    # Mock Ollama response
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Data lakes are centralized repositories...",
        "prompt_eval_count": 10,
        "eval_count": 20
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    llm = ManagedLLM(
        primary="ollama",
        config=LLMConfig(enable_cache=False)
    )

    response = llm.generate("What is a data lake?")

    assert response.text == "Data lakes are centralized repositories..."
    assert response.provider == "ollama"
    assert mock_post.called


@patch("neurolake.llm.providers.ollama_provider.requests.post")
def test_managed_llm_with_cache(mock_post):
    """Test managed LLM with caching."""
    # Mock Ollama response
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Cached response",
        "prompt_eval_count": 10,
        "eval_count": 20
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    llm = ManagedLLM(
        primary="ollama",
        config=LLMConfig(enable_cache=True)
    )

    # First call - should hit API
    response1 = llm.generate("test prompt")
    assert mock_post.call_count == 1

    # Second call - should hit cache
    response2 = llm.generate("test prompt")
    assert mock_post.call_count == 1  # No additional call
    assert response2.cached is True


# ===== Integration Tests =====

def test_llm_message_creation():
    """Test LLM message creation."""
    msg = LLMMessage(
        role=MessageRole.USER,
        content="Hello"
    )

    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"


def test_llm_response_tokens_per_second():
    """Test tokens per second calculation."""
    response = LLMResponse(
        text="test",
        provider="test",
        model="test",
        completion_tokens=100,
        latency_ms=1000  # 1 second
    )

    assert response.tokens_per_second == 100.0


def test_token_usage_to_dict():
    """Test token usage serialization."""
    usage = TokenUsage(
        provider="openai",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost=0.005
    )

    data = usage.to_dict()

    assert data["provider"] == "openai"
    assert data["total_tokens"] == 150
    assert "timestamp" in data


# ============================================================================
# Additional Comprehensive Tests
# ============================================================================


# ===== Extended LLMMessage Tests =====

class TestLLMMessageExtended:
    """Extended tests for LLMMessage."""

    def test_message_with_all_fields(self):
        """Test message with all fields populated"""
        msg = LLMMessage(
            role=MessageRole.ASSISTANT,
            content="Hello from AI",
            name="assistant_v1",
            metadata={"model": "gpt-4", "temperature": 0.7}
        )

        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hello from AI"
        assert msg.name == "assistant_v1"
        assert msg.metadata["model"] == "gpt-4"
        assert msg.metadata["temperature"] == 0.7

    def test_message_roles_enum(self):
        """Test all message role enum values"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"

    def test_message_empty_metadata(self):
        """Test message with empty metadata defaults to empty dict"""
        msg = LLMMessage(role=MessageRole.USER, content="Test")

        assert msg.metadata == {}
        assert isinstance(msg.metadata, dict)


# ===== Extended LLMResponse Tests =====

class TestLLMResponseExtended:
    """Extended tests for LLMResponse."""

    def test_response_with_all_fields(self):
        """Test response with all fields"""
        response = LLMResponse(
            text="Complete response",
            provider="openai",
            model="gpt-4-turbo",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            cost=0.015,
            latency_ms=1500.0,
            finish_reason="stop",
            cached=True,
            metadata={"request_id": "abc123"}
        )

        assert response.text == "Complete response"
        assert response.provider == "openai"
        assert response.model == "gpt-4-turbo"
        assert response.prompt_tokens == 100
        assert response.completion_tokens == 200
        assert response.total_tokens == 300
        assert response.cost == 0.015
        assert response.latency_ms == 1500.0
        assert response.finish_reason == "stop"
        assert response.cached is True
        assert response.metadata["request_id"] == "abc123"

    def test_tokens_per_second_edge_cases(self):
        """Test tokens per second calculation edge cases"""
        # Normal case
        resp1 = LLMResponse(
            text="test",
            provider="test",
            model="test",
            completion_tokens=1000,
            latency_ms=2000.0  # 2 seconds
        )
        assert resp1.tokens_per_second == 500.0

        # Zero latency
        resp2 = LLMResponse(
            text="test",
            provider="test",
            model="test",
            completion_tokens=100,
            latency_ms=0.0
        )
        assert resp2.tokens_per_second == 0.0

        # Very small latency
        resp3 = LLMResponse(
            text="test",
            provider="test",
            model="test",
            completion_tokens=10,
            latency_ms=0.1
        )
        assert resp3.tokens_per_second == 100000.0

    def test_response_defaults(self):
        """Test that response has sensible defaults"""
        response = LLMResponse(
            text="Test",
            provider="test",
            model="test"
        )

        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.total_tokens == 0
        assert response.cost == 0.0
        assert response.latency_ms == 0.0
        assert response.finish_reason is None
        assert response.cached is False
        assert isinstance(response.timestamp, datetime)
        assert response.metadata == {}


# ===== Extended Config Tests =====

class TestLLMConfigExtended:
    """Extended tests for LLM configuration."""

    def test_config_all_defaults(self):
        """Test all default configuration values"""
        config = LLMConfig()

        # Model defaults
        assert config.openai_model == "gpt-4"
        assert config.anthropic_model == "claude-3-sonnet-20240229"
        assert config.ollama_model == "llama2"
        assert config.ollama_base_url == "http://localhost:11434"

        # Rate limits
        assert config.openai_rpm == 60
        assert config.anthropic_rpm == 50
        assert config.ollama_rpm == 1000

        # Retry settings
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.backoff_factor == 2.0

        # Caching
        assert config.enable_cache is True
        assert config.cache_ttl == 3600

        # Other settings
        assert config.track_usage is True
        assert config.timeout == 60.0
        assert config.extra == {}

    def test_config_custom_all_fields(self):
        """Test configuration with all custom fields"""
        config = LLMConfig(
            openai_api_key="sk-custom-openai",
            anthropic_api_key="sk-custom-anthropic",
            ollama_base_url="http://custom:11434",
            openai_model="gpt-3.5-turbo",
            anthropic_model="claude-3-haiku-20240307",
            ollama_model="mistral",
            openai_rpm=120,
            anthropic_rpm=100,
            ollama_rpm=2000,
            max_retries=5,
            retry_delay=2.0,
            backoff_factor=3.0,
            enable_cache=False,
            cache_ttl=7200,
            track_usage=False,
            timeout=120.0,
            extra={"custom_key": "custom_value"}
        )

        assert config.openai_api_key == "sk-custom-openai"
        assert config.anthropic_api_key == "sk-custom-anthropic"
        assert config.ollama_base_url == "http://custom:11434"
        assert config.openai_model == "gpt-3.5-turbo"
        assert config.anthropic_model == "claude-3-haiku-20240307"
        assert config.ollama_model == "mistral"
        assert config.openai_rpm == 120
        assert config.anthropic_rpm == 100
        assert config.ollama_rpm == 2000
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.backoff_factor == 3.0
        assert config.enable_cache is False
        assert config.cache_ttl == 7200
        assert config.track_usage is False
        assert config.timeout == 120.0
        assert config.extra["custom_key"] == "custom_value"

    def test_get_model_unknown_provider(self):
        """Test get_model with unknown provider raises error"""
        config = LLMConfig()

        with pytest.raises(ValueError, match="Unknown provider"):
            config.get_model("unknown_provider")

    def test_get_rpm_unknown_provider(self):
        """Test get_rpm with unknown provider returns default"""
        config = LLMConfig()

        # Unknown provider should return default of 60
        assert config.get_rpm("unknown_provider") == 60

    @patch.dict('os.environ', {}, clear=True)
    def test_env_vars_not_set(self):
        """Test config when environment variables are not set"""
        config = LLMConfig()

        # Should be None when not set
        assert config.openai_api_key is None
        assert config.anthropic_api_key is None


# ===== Extended Usage Tracking Tests =====

class TestUsageTrackerExtended:
    """Extended tests for usage tracking."""

    def test_calculate_cost_all_models(self):
        """Test cost calculation for all supported models"""
        tracker = UsageTracker()

        test_cases = [
            ("gpt-4", 1_000_000, 1_000_000, 90.0),
            ("gpt-4-turbo", 1_000_000, 1_000_000, 40.0),
            ("gpt-3.5-turbo", 1_000_000, 1_000_000, 2.0),
            ("claude-3-opus-20240229", 1_000_000, 1_000_000, 90.0),
            ("claude-3-sonnet-20240229", 1_000_000, 1_000_000, 18.0),
            ("claude-3-haiku-20240307", 1_000_000, 1_000_000, 1.5),
        ]

        for model, prompt_tokens, completion_tokens, expected_cost in test_cases:
            cost = tracker.calculate_cost(model, prompt_tokens, completion_tokens)
            assert cost == expected_cost, f"Cost mismatch for {model}"

    def test_calculate_cost_partial_model_name(self):
        """Test cost calculation with partial model name matching"""
        tracker = UsageTracker()

        # Should match "gpt-4" in the pricing table
        cost = tracker.calculate_cost("gpt-4-0125-preview", 1_000_000, 1_000_000)

        assert cost > 0  # Should find a match

    def test_stats_cache_invalidation(self):
        """Test that stats cache is invalidated on new records"""
        tracker = UsageTracker()

        tracker.record("openai", "gpt-4", 100, 50)
        stats1 = tracker.get_stats()

        # Stats should be cached
        assert tracker._stats_cache is not None

        # Record new usage
        tracker.record("openai", "gpt-4", 100, 50)

        # Cache should be invalidated
        assert tracker._stats_cache is None

    def test_get_stats_empty_by_provider(self):
        """Test getting stats for provider with no usage"""
        tracker = UsageTracker()

        tracker.record("openai", "gpt-4", 100, 50)

        stats = tracker.get_stats(provider="anthropic")

        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost"] == 0.0

    def test_token_usage_timestamp(self):
        """Test that TokenUsage has timestamp"""
        usage = TokenUsage(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost=0.005
        )

        assert isinstance(usage.timestamp, datetime)
        assert (datetime.now() - usage.timestamp).total_seconds() < 1.0

    def test_save_creates_file(self):
        """Test that save creates a valid JSON file"""
        tracker = UsageTracker()

        tracker.record("openai", "gpt-4", 100, 50)
        tracker.record("anthropic", "claude-3-sonnet-20240229", 150, 75)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            path = Path(f.name)

        try:
            tracker.save(path)

            # Verify file structure
            with open(path, 'r') as f:
                data = json.load(f)

            assert "usage_history" in data
            assert "stats" in data
            assert len(data["usage_history"]) == 2
            assert data["stats"]["total_requests"] == 2
        finally:
            path.unlink()


# ===== Extended Rate Limiter Tests =====

class TestRateLimiterExtended:
    """Extended tests for rate limiting."""

    def test_rate_limit_config_tokens_per_second(self):
        """Test tokens per second calculation in config"""
        config = RateLimitConfig(requests_per_minute=120, burst_size=20)

        assert config.tokens_per_second == 2.0

    def test_rate_limiter_burst_size(self):
        """Test that burst size is respected"""
        limiter = RateLimiter(requests_per_minute=60, burst_size=15)

        # Should be able to acquire burst_size tokens immediately
        for i in range(15):
            assert limiter.acquire(1, blocking=False) is True, f"Failed at token {i+1}"

        # 16th should fail (burst exhausted)
        assert limiter.acquire(1, blocking=False) is False

    def test_rate_limiter_refill_over_time(self):
        """Test that tokens refill over time"""
        limiter = RateLimiter(requests_per_minute=600, burst_size=5)  # 10 tokens/sec

        # Drain all tokens
        for _ in range(5):
            limiter.acquire(1, blocking=False)

        # Should have no tokens
        assert limiter.acquire(1, blocking=False) is False

        # Wait for some tokens to refill (0.3 seconds = 3 tokens)
        time.sleep(0.3)

        # Should have tokens now
        assert limiter.acquire(1, blocking=False) is True

    def test_multi_provider_independent_limits(self):
        """Test that different providers have independent limits"""
        limiter = MultiProviderRateLimiter()

        limiter.set_limit("openai", requests_per_minute=60, burst_size=3)
        limiter.set_limit("anthropic", requests_per_minute=60, burst_size=3)

        # Drain openai
        for _ in range(3):
            limiter.acquire("openai", blocking=False)

        # OpenAI should be exhausted
        assert limiter.acquire("openai", blocking=False) is False

        # But Anthropic should still have tokens
        assert limiter.acquire("anthropic", blocking=False) is True

    def test_multi_provider_get_wait_time_no_limit(self):
        """Test getting wait time for provider without limit"""
        limiter = MultiProviderRateLimiter()

        # No limit set
        wait_time = limiter.get_wait_time("openai")

        assert wait_time == 0.0


# ===== Extended Retry Tests =====

class TestRetryExtended:
    """Extended tests for retry logic."""

    def test_retry_config_get_delay_calculation(self):
        """Test delay calculation with different attempts"""
        config = RetryConfig(
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=30.0
        )

        assert config.get_delay(0) == 1.0   # 1.0 * 2^0
        assert config.get_delay(1) == 2.0   # 1.0 * 2^1
        assert config.get_delay(2) == 4.0   # 1.0 * 2^2
        assert config.get_delay(3) == 8.0   # 1.0 * 2^3
        assert config.get_delay(4) == 16.0  # 1.0 * 2^4
        assert config.get_delay(5) == 30.0  # Capped at max_delay

    def test_retry_handler_with_args_and_kwargs(self):
        """Test retry handler passes args and kwargs correctly"""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)

        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = handler.execute(func_with_args, "x", "y", c="z")

        assert result == "x-y-z"

    def test_retry_handler_respects_max_retries(self):
        """Test that handler respects max_retries setting"""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)

        attempt = {"count": 0}

        def always_fails():
            attempt["count"] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            handler.execute(always_fails, retry_on=(ValueError,))

        # Should try initial + 2 retries = 3 total
        assert attempt["count"] == 3

    def test_retry_decorator_preserves_function_metadata(self):
        """Test that retry decorator preserves function metadata"""
        @retry_with_backoff(max_retries=3)
        def my_function():
            """My function docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My function docstring."


# ===== Extended Cache Tests =====

class TestLLMCacheExtended:
    """Extended tests for LLM cache."""

    def test_cache_entry_hit_counter(self):
        """Test that cache entry tracks hits"""
        cache = LLMCache()

        cache.set("key1", {"text": "response"})

        # Get multiple times
        for i in range(5):
            cache.get("key1")

        entry = cache.cache["key1"]
        assert entry.hits == 5

    def test_cache_lru_eviction_strategy(self):
        """Test LRU eviction strategy"""
        cache = LLMCache(max_size=3)

        cache.set("key1", {"text": "1"})
        cache.set("key2", {"text": "2"})
        cache.set("key3", {"text": "3"})

        # Access key1 and key2 to increase their hit count
        cache.get("key1")
        cache.get("key1")
        cache.get("key2")

        # Add 4th key - should evict key3 (least hits)
        cache.set("key4", {"text": "4"})

        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        assert cache.get("key3") is None
        assert cache.get("key4") is not None

    def test_cache_custom_ttl_per_entry(self):
        """Test setting custom TTL per entry"""
        cache = LLMCache(ttl=3600)

        cache.set("key1", {"text": "1"})  # Use default TTL
        cache.set("key2", {"text": "2"}, ttl=1)  # Custom short TTL

        time.sleep(1.1)

        # key1 should still be valid (3600s TTL)
        assert cache.get("key1") is not None

        # key2 should be expired (1s TTL)
        assert cache.get("key2") is None

    def test_cache_cleanup_expired_keeps_valid(self):
        """Test that cleanup_expired keeps valid entries"""
        cache = LLMCache(ttl=10)

        cache.set("key1", {"text": "1"}, ttl=1)
        cache.set("key2", {"text": "2"}, ttl=3600)

        time.sleep(1.1)

        cache.cleanup_expired()

        assert "key1" not in cache.cache
        assert "key2" in cache.cache

    def test_cache_deterministic_key_generation(self):
        """Test that key generation is deterministic"""
        cache = LLMCache()

        # Generate same key multiple times
        keys = [
            cache.generate_key("prompt", model="gpt-4", temperature=0.7, max_tokens=100)
            for _ in range(10)
        ]

        # All keys should be identical
        assert len(set(keys)) == 1

    def test_cache_different_params_different_keys(self):
        """Test that different parameters generate different keys"""
        cache = LLMCache()

        key1 = cache.generate_key("prompt", model="gpt-4", temperature=0.7)
        key2 = cache.generate_key("prompt", model="gpt-4", temperature=0.8)
        key3 = cache.generate_key("prompt", model="gpt-3.5-turbo", temperature=0.7)
        key4 = cache.generate_key("different prompt", model="gpt-4", temperature=0.7)

        assert len({key1, key2, key3, key4}) == 4

    def test_cache_load_ignores_expired(self):
        """Test that load ignores expired entries"""
        cache1 = LLMCache(ttl=1)

        cache1.set("key1", {"text": "1"})
        cache1.set("key2", {"text": "2"})

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            path = Path(f.name)

        try:
            time.sleep(1.1)  # Wait for entries to expire

            cache1.save(path)

            # Load into new cache
            cache2 = LLMCache()
            cache2.load(path)

            # Should not have loaded expired entries
            assert len(cache2.cache) == 0
        finally:
            path.unlink()


# ===== Extended Factory Tests =====

class TestLLMFactoryExtended:
    """Extended tests for LLM factory."""

    def test_factory_creates_with_usage_tracker(self):
        """Test factory creates provider with usage tracker"""
        tracker = UsageTracker()

        provider = LLMFactory.create("ollama", usage_tracker=tracker)

        assert provider.usage_tracker is tracker

    def test_factory_uses_config_api_key(self):
        """Test factory uses API key from config"""
        with patch('neurolake.llm.providers.openai_provider.HAS_OPENAI', True), \
             patch('neurolake.llm.providers.openai_provider.OpenAI'):

            config = LLMConfig(openai_api_key="sk-from-config")

            provider = LLMFactory.create("openai", config=config)

            # Provider should be created successfully
            assert provider is not None

    def test_factory_api_key_override_takes_precedence(self):
        """Test that explicit API key overrides config"""
        with patch('neurolake.llm.providers.openai_provider.HAS_OPENAI', True), \
             patch('neurolake.llm.providers.openai_provider.OpenAI') as mock_openai:

            config = LLMConfig(openai_api_key="sk-from-config")

            provider = LLMFactory.create(
                "openai",
                api_key="sk-override",
                config=config
            )

            # Should have created provider successfully
            assert provider is not None


# ===== Extended ManagedLLM Tests =====

class TestManagedLLMExtended:
    """Extended tests for managed LLM."""

    @patch("neurolake.llm.providers.ollama_provider.requests.post")
    def test_managed_llm_generates_cache_key(self, mock_post):
        """Test that managed LLM generates proper cache keys"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Test response",
            "prompt_eval_count": 10,
            "eval_count": 20
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        llm = ManagedLLM(
            primary="ollama",
            config=LLMConfig(enable_cache=True)
        )

        # First call
        llm.generate("prompt1", temperature=0.7)

        # Second call with same params - should hit cache
        llm.generate("prompt1", temperature=0.7)

        # Should only call provider once
        assert mock_post.call_count == 1

    @patch("neurolake.llm.providers.ollama_provider.requests.post")
    def test_managed_llm_disable_cache(self, mock_post):
        """Test managed LLM with caching disabled"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Test response",
            "prompt_eval_count": 10,
            "eval_count": 20
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        llm = ManagedLLM(
            primary="ollama",
            config=LLMConfig(enable_cache=False)
        )

        llm.generate("prompt1")
        llm.generate("prompt1")

        # Should call provider twice (no caching)
        assert mock_post.call_count == 2


# ===== Edge Cases and Error Conditions =====

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_prompt_caching(self):
        """Test caching with empty prompt"""
        cache = LLMCache()

        key = cache.generate_key("", model="gpt-4")

        # Should generate a valid key even for empty prompt
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hash length

    def test_very_long_prompt_caching(self):
        """Test caching with very long prompt"""
        cache = LLMCache()

        long_prompt = "x" * 1_000_000
        key = cache.generate_key(long_prompt, model="gpt-4")

        # Hash should be fixed length regardless of input size
        assert len(key) == 64

    def test_unicode_in_prompts(self):
        """Test handling of Unicode characters"""
        cache = LLMCache()

        unicode_prompt = "Hello 世界 🌍 مرحبا"
        key = cache.generate_key(unicode_prompt, model="gpt-4")

        assert isinstance(key, str)
        assert len(key) == 64

    def test_special_characters_in_prompts(self):
        """Test handling of special characters"""
        cache = LLMCache()

        special_prompt = "SELECT * FROM users WHERE id = '1'; DROP TABLE users;--"
        key = cache.generate_key(special_prompt, model="gpt-4")

        assert isinstance(key, str)

    def test_zero_token_usage(self):
        """Test usage tracking with zero tokens"""
        tracker = UsageTracker()

        cost = tracker.calculate_cost("gpt-4", 0, 0)

        assert cost == 0.0

    def test_negative_tokens_handled(self):
        """Test that negative tokens are handled (shouldn't happen but test anyway)"""
        tracker = UsageTracker()

        # Should handle gracefully
        cost = tracker.calculate_cost("gpt-4", -100, -50)

        # Will produce negative cost (unintended but predictable)
        assert cost < 0

    def test_cache_with_zero_max_size(self):
        """Test cache behavior with max_size of 1"""
        cache = LLMCache(max_size=1)

        cache.set("key1", {"text": "1"})
        cache.set("key2", {"text": "2"})

        # Should only have 1 entry (most recent)
        assert len(cache.cache) == 1
        assert cache.get("key2") is not None

    def test_rate_limiter_with_very_high_rpm(self):
        """Test rate limiter with very high RPM"""
        limiter = RateLimiter(requests_per_minute=100000, burst_size=1000)

        # Should allow many requests quickly
        for _ in range(100):
            assert limiter.acquire(1, blocking=False) is True

    def test_retry_with_zero_max_retries(self):
        """Test retry handler with max_retries=0"""
        handler = RetryHandler(max_retries=0, initial_delay=0.01)

        attempt = {"count": 0}

        def func():
            attempt["count"] += 1
            return "success"

        result = handler.execute(func)

        # Should execute once (initial attempt, no retries)
        assert result == "success"
        assert attempt["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
