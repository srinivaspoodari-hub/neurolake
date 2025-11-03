"""
OpenAI Provider

Implements LLMProvider for OpenAI's GPT models.
"""

import time
from typing import List, Optional, Iterator
import logging

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage, MessageRole
from neurolake.llm.usage import UsageTracker

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """
    OpenAI LLM provider for GPT models.

    Example:
        provider = OpenAIProvider(api_key="sk-...", model="gpt-4")

        response = provider.generate("Explain data lakes")
        print(response.text)
        print(f"Cost: ${response.cost:.4f}")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        usage_tracker: Optional[UsageTracker] = None
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            usage_tracker: Optional usage tracker
        """
        if not HAS_OPENAI:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai"
            )

        self.client = OpenAI(api_key=api_key)
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
        """Generate response from OpenAI."""
        start_time = time.time()

        # Build messages
        msg_list = []

        if system:
            msg_list.append({"role": "system", "content": system})

        if messages:
            for msg in messages:
                msg_list.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        msg_list.append({"role": "user", "content": prompt})

        # Make API call
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=msg_list,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                **kwargs
            )

            # Extract response
            text = completion.choices[0].message.content
            finish_reason = completion.choices[0].finish_reason

            # Extract usage
            usage = completion.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            cost = self.usage_tracker.record(
                provider="openai",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                text=text,
                provider="openai",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                finish_reason=finish_reason
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        """Stream response from OpenAI."""
        # Build messages
        msg_list = []

        if system:
            msg_list.append({"role": "system", "content": system})

        if messages:
            for msg in messages:
                msg_list.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        msg_list.append({"role": "user", "content": prompt})

        # Make streaming API call
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=msg_list,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                stream=True,
                **kwargs
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Note: This is an approximation. For exact counts, use tiktoken.
        """
        # Rough approximation: ~4 characters per token
        return len(text) // 4

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "openai"


__all__ = ["OpenAIProvider"]
