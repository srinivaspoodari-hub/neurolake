"""
Ollama Provider

Implements LLMProvider for local Ollama models.
"""

import time
import requests
from typing import List, Optional, Iterator, Dict, Any
import logging

from neurolake.llm.provider import LLMProvider, LLMResponse, LLMMessage, MessageRole
from neurolake.llm.usage import UsageTracker

logger = logging.getLogger(__name__)


class OllamaProvider:
    """
    Ollama LLM provider for local models.

    Example:
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            model="llama2"
        )

        response = provider.generate("Explain data lakes")
        print(response.text)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        usage_tracker: Optional[UsageTracker] = None
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL
            model: Model name
            usage_tracker: Optional usage tracker
        """
        self.base_url = base_url.rstrip("/")
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
        """Generate response from Ollama."""
        start_time = time.time()

        # Build messages or use simple prompt
        if messages or system:
            # Use chat endpoint
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

            payload = {
                "model": self.model,
                "messages": msg_list,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens or -1,
                    "stop": stop or [],
                    **kwargs
                }
            }

            endpoint = f"{self.base_url}/api/chat"

        else:
            # Use generate endpoint
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens or -1,
                    "stop": stop or [],
                    **kwargs
                }
            }

            endpoint = f"{self.base_url}/api/generate"

        # Make API call
        try:
            response = requests.post(endpoint, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            # Extract response
            if "message" in data:
                # Chat endpoint
                text = data["message"]["content"]
            else:
                # Generate endpoint
                text = data["response"]

            # Extract tokens (Ollama provides these)
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost (Ollama is free)
            cost = 0.0

            # Record usage
            self.usage_tracker.record(
                provider="ollama",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                text=text,
                provider="ollama",
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                finish_reason="stop"
            )

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
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
        """Stream response from Ollama."""
        # Build messages or use simple prompt
        if messages or system:
            # Use chat endpoint
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

            payload = {
                "model": self.model,
                "messages": msg_list,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens or -1,
                    "stop": stop or [],
                    **kwargs
                }
            }

            endpoint = f"{self.base_url}/api/chat"
            content_key = "message"

        else:
            # Use generate endpoint
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens or -1,
                    "stop": stop or [],
                    **kwargs
                }
            }

            endpoint = f"{self.base_url}/api/generate"
            content_key = "response"

        # Make streaming API call
        try:
            response = requests.post(
                endpoint,
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)

                    if content_key == "message":
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    else:
                        if "response" in data:
                            yield data["response"]

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
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
        return "ollama"


__all__ = ["OllamaProvider"]
