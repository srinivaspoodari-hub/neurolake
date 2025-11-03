"""
LLM Provider Protocol

Defines the interface that all LLM providers must implement.
"""

from typing import Protocol, List, Optional, Dict, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageRole(Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second."""
        if self.latency_ms > 0:
            return (self.completion_tokens / self.latency_ms) * 1000
        return 0.0


class LLMProvider(Protocol):
    """
    Protocol defining the interface for LLM providers.

    All providers must implement these methods.
    """

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system: Optional system message
            messages: Optional conversation history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        ...

    def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream response from the LLM.

        Args:
            Same as generate()

        Yields:
            Text chunks as they arrive
        """
        ...

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        ...

    def get_model_name(self) -> str:
        """Get the model name."""
        ...

    def get_provider_name(self) -> str:
        """Get the provider name."""
        ...


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMMessage",
    "MessageRole",
]
