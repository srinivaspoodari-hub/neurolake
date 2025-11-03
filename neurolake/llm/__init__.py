"""
NeuroLake LLM Module

Unified interface for multiple LLM providers with rate limiting, caching, and fallbacks.

Example:
    from neurolake.llm import LLMFactory, LLMConfig

    # Create provider
    llm = LLMFactory.create("openai", api_key="sk-...")

    # Generate response
    response = llm.generate("Explain data lakes", max_tokens=100)
    print(response.text)
    print(f"Cost: ${response.cost:.4f}")

    # Streaming
    for chunk in llm.stream("Write a query"):
        print(chunk, end="")
"""

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage
from neurolake.llm.factory import LLMFactory
from neurolake.llm.config import LLMConfig
from neurolake.llm.usage import UsageTracker, TokenUsage

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMMessage",
    "LLMFactory",
    "LLMConfig",
    "UsageTracker",
    "TokenUsage",
]
