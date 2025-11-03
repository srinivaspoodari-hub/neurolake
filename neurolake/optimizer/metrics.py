"""
Optimization Metrics Tracking

Track and report on query optimization performance and transformations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class OptimizationMetrics:
    """
    Metrics for a single optimization run.

    Tracks transformations, timing, and rule applications.
    """

    query_id: str
    original_sql: str
    optimized_sql: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    optimization_time_ms: float = 0.0
    rules_applied: List[str] = field(default_factory=list)
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    skipped: bool = False
    error: Optional[str] = None

    def add_transformation(
        self,
        rule_name: str,
        before: str,
        after: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a transformation.

        Args:
            rule_name: Name of rule that applied transformation
            before: SQL before transformation
            after: SQL after transformation
            metadata: Additional transformation metadata
        """
        self.rules_applied.append(rule_name)
        self.transformations.append({
            "rule": rule_name,
            "before": before,
            "after": after,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })

    def complete(self):
        """Mark optimization as complete and calculate duration."""
        self.end_time = datetime.now()
        if self.start_time:
            delta = self.end_time - self.start_time
            self.optimization_time_ms = delta.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_id": self.query_id,
            "original_sql": self.original_sql,
            "optimized_sql": self.optimized_sql,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "optimization_time_ms": self.optimization_time_ms,
            "rules_applied": self.rules_applied,
            "transformation_count": len(self.transformations),
            "transformations": self.transformations,
            "enabled": self.enabled,
            "skipped": self.skipped,
            "error": self.error,
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        lines = []
        lines.append(f"Query ID: {self.query_id}")
        lines.append(f"Optimization Time: {self.optimization_time_ms:.2f}ms")
        lines.append(f"Rules Applied: {len(self.rules_applied)}")

        if self.rules_applied:
            lines.append(f"  - {', '.join(self.rules_applied)}")

        lines.append(f"Transformations: {len(self.transformations)}")

        if self.error:
            lines.append(f"Error: {self.error}")

        return "\n".join(lines)


class MetricsCollector:
    """
    Collects and aggregates optimization metrics.

    Tracks metrics across multiple optimization runs for analysis.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics to retain
        """
        self.max_history = max_history
        self.metrics_history: List[OptimizationMetrics] = []
        self.total_optimizations = 0
        self.total_transformations = 0
        self.total_optimization_time_ms = 0.0

    def record(self, metrics: OptimizationMetrics):
        """
        Record optimization metrics.

        Args:
            metrics: OptimizationMetrics instance
        """
        self.metrics_history.append(metrics)
        self.total_optimizations += 1
        self.total_transformations += len(metrics.transformations)
        self.total_optimization_time_ms += metrics.optimization_time_ms

        # Trim history if needed
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]

    def get_recent(self, limit: int = 10) -> List[OptimizationMetrics]:
        """Get recent metrics."""
        return self.metrics_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics.

        Returns:
            Dictionary with aggregate stats
        """
        if not self.metrics_history:
            return {
                "total_optimizations": 0,
                "total_transformations": 0,
                "avg_optimization_time_ms": 0.0,
                "avg_transformations_per_query": 0.0,
            }

        return {
            "total_optimizations": self.total_optimizations,
            "total_transformations": self.total_transformations,
            "avg_optimization_time_ms": self.total_optimization_time_ms / self.total_optimizations,
            "avg_transformations_per_query": self.total_transformations / self.total_optimizations,
            "recent_count": len(self.metrics_history),
        }

    def get_rule_stats(self) -> Dict[str, int]:
        """
        Get rule application statistics.

        Returns:
            Dictionary mapping rule names to application counts
        """
        rule_counts = {}
        for metrics in self.metrics_history:
            for rule_name in metrics.rules_applied:
                rule_counts[rule_name] = rule_counts.get(rule_name, 0) + 1

        return dict(sorted(rule_counts.items(), key=lambda x: x[1], reverse=True))

    def clear(self):
        """Clear all metrics."""
        self.metrics_history.clear()
        self.total_optimizations = 0
        self.total_transformations = 0
        self.total_optimization_time_ms = 0.0

    def __len__(self) -> int:
        return len(self.metrics_history)

    def __repr__(self) -> str:
        return f"MetricsCollector(optimizations={self.total_optimizations}, transformations={self.total_transformations})"


__all__ = [
    "OptimizationMetrics",
    "MetricsCollector",
]
