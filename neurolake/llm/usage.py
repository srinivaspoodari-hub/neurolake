"""
Usage Tracking

Track token usage and cost across LLM providers.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path


# Pricing per 1M tokens (as of 2025)
PRICING = {
    "gpt-4": {"prompt": 30.0, "completion": 60.0},
    "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
    "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
    "claude-3-opus-20240229": {"prompt": 15.0, "completion": 75.0},
    "claude-3-sonnet-20240229": {"prompt": 3.0, "completion": 15.0},
    "claude-3-haiku-20240307": {"prompt": 0.25, "completion": 1.25},
    # Ollama is free
    "ollama": {"prompt": 0.0, "completion": 0.0},
}


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class UsageTracker:
    """
    Track token usage and cost across all LLM calls.

    Example:
        tracker = UsageTracker()

        # Record usage
        tracker.record(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50
        )

        # Get statistics
        stats = tracker.get_stats()
        print(f"Total cost: ${stats['total_cost']:.2f}")
    """

    def __init__(self):
        """Initialize usage tracker."""
        self.usage_history: List[TokenUsage] = []
        self._stats_cache: Optional[Dict] = None

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Record token usage and calculate cost.

        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        usage = TokenUsage(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost
        )

        self.usage_history.append(usage)
        self._stats_cache = None  # Invalidate cache

        return cost

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost for a request."""
        # Get pricing for model
        pricing = PRICING.get(model)
        if not pricing:
            # Try to match partial model name
            for key in PRICING:
                if key in model.lower():
                    pricing = PRICING[key]
                    break

        if not pricing:
            pricing = {"prompt": 0.0, "completion": 0.0}

        # Calculate cost (pricing is per 1M tokens)
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]

        return prompt_cost + completion_cost

    def get_stats(self, provider: Optional[str] = None) -> Dict:
        """Get usage statistics."""
        if self._stats_cache and provider is None:
            return self._stats_cache

        history = self.usage_history
        if provider:
            history = [u for u in history if u.provider == provider]

        if not history:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_provider": {},
                "by_model": {}
            }

        total_requests = len(history)
        total_tokens = sum(u.total_tokens for u in history)
        total_cost = sum(u.cost for u in history)

        # By provider
        by_provider: Dict[str, Dict] = {}
        for usage in history:
            if usage.provider not in by_provider:
                by_provider[usage.provider] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            by_provider[usage.provider]["requests"] += 1
            by_provider[usage.provider]["tokens"] += usage.total_tokens
            by_provider[usage.provider]["cost"] += usage.cost

        # By model
        by_model: Dict[str, Dict] = {}
        for usage in history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            by_model[usage.model]["requests"] += 1
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["cost"] += usage.cost

        stats = {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_provider": by_provider,
            "by_model": by_model
        }

        if provider is None:
            self._stats_cache = stats

        return stats

    def save(self, path: Path):
        """Save usage history to file."""
        data = {
            "usage_history": [u.to_dict() for u in self.usage_history],
            "stats": self.get_stats()
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def reset(self):
        """Reset usage history."""
        self.usage_history = []
        self._stats_cache = None


__all__ = ["UsageTracker", "TokenUsage", "PRICING"]
