"""
Anthropic Provider

Implements LLMProvider for Anthropic's Claude models.
"""

import time
from typing import List, Optional, Iterator
import logging

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage, MessageRole
from neurolake.llm.usage import UsageTracker

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """
    Anthropic LLM provider for Claude models.

    Example:
        provider = AnthropicProvider(
            api_key="sk-ant-...",
            model="claude-3-sonnet-20240229"
        )

        response = provider.generate("Explain data lakes")
        print(response.text)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        usage_tracker: Optional[UsageTracker] = None
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name
            usage_tracker: Optional usage tracker
        """
        if not HAS_ANTHROPIC:
            raise ImportError(
                "Anthropic library not installed. Install with: pip install anthropic"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.usage_tracker = usage_tracker or UsageTracker()

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
        """Generate response from Anthropic."""
        start_time = time.time()

        # Build messages
        msg_list = []

        if messages:
            for msg in messages:
                msg_list.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        msg_list.append({"role": "user", "content": prompt})

        # Make API call
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1024,
                system=system,
                messages=msg_list,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                **kwargs
            )

            # Extract response
            text = message.content[0].text
            finish_reason = message.stop_reason

            # Extract usage
            prompt_tokens = message.usage.input_tokens
            completion_tokens = message.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost
            cost = self.usage_tracker.record(
                provider="anthropic",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                text=text,
                provider="anthropic",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                finish_reason=finish_reason
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

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
        """Stream response from Anthropic."""
        # Build messages
        msg_list = []

        if messages:
            for msg in messages:
                msg_list.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        msg_list.append({"role": "user", "content": prompt})

        # Make streaming API call
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or 1024,
                system=system,
                messages=msg_list,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                **kwargs
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Note: This is an approximation.
        """
        # Rough approximation: ~4 characters per token
        return len(text) // 4

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "anthropic"


__all__ = ["AnthropicProvider"]
