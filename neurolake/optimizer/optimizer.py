"""
Query Optimizer

Main optimizer class that applies optimization rules to SQL queries.
"""

from typing import List, Optional, Dict, Any, Tuple
import logging
import uuid
from datetime import datetime

from neurolake.optimizer.rules import OptimizationRule, RuleRegistry, get_rule_registry
from neurolake.optimizer.metrics import OptimizationMetrics, MetricsCollector

logger = logging.getLogger("neurolake.optimizer")


class QueryOptimizer:
    """
    SQL Query Optimizer with rule-based transformations.

    Applies a chain of optimization rules to SQL queries to improve
    performance, readability, and efficiency.

    Features:
    - Rule-based optimization
    - Enable/disable optimization
    - Metrics tracking
    - Transformation logging
    - Configurable rule execution

    Example:
        optimizer = QueryOptimizer(enabled=True)
        optimized_sql = optimizer.optimize("SELECT * FROM users WHERE 1=1")

        # Get metrics
        stats = optimizer.get_stats()
        print(f"Applied {stats['total_transformations']} transformations")
    """

    def __init__(
        self,
        enabled: bool = True,
        registry: Optional[RuleRegistry] = None,
        track_metrics: bool = True,
        log_transformations: bool = True,
        max_iterations: int = 10,
    ):
        """
        Initialize query optimizer.

        Args:
            enabled: Whether optimizer is active
            registry: Custom rule registry (uses global if None)
            track_metrics: Whether to track optimization metrics
            log_transformations: Whether to log transformations
            max_iterations: Maximum rule application iterations
        """
        self.enabled = enabled
        self.registry = registry or get_rule_registry()
        self.track_metrics = track_metrics
        self.log_transformations = log_transformations
        self.max_iterations = max_iterations

        # Metrics collection
        self.metrics_collector = MetricsCollector() if track_metrics else None

    def optimize(
        self,
        sql: str,
        query_id: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> str:
        """
        Optimize SQL query.

        Args:
            sql: Original SQL query
            query_id: Optional query identifier
            categories: Optional list of rule categories to apply

        Returns:
            Optimized SQL query

        Example:
            # Optimize with all rules
            optimized = optimizer.optimize("SELECT * FROM users WHERE 1=1")

            # Optimize with specific categories
            optimized = optimizer.optimize(
                "SELECT * FROM users",
                categories=["predicate", "projection"]
            )
        """
        # If optimizer disabled, return original SQL
        if not self.enabled:
            if self.log_transformations:
                logger.info(f"Optimizer disabled, skipping optimization")
            return sql

        # Generate query ID if not provided
        query_id = query_id or str(uuid.uuid4())

        # Initialize metrics
        metrics = None
        if self.track_metrics:
            metrics = OptimizationMetrics(
                query_id=query_id,
                original_sql=sql,
                optimized_sql=sql,
                enabled=self.enabled,
            )

        try:
            # Apply optimization rules
            optimized_sql = self._apply_rules(sql, metrics, categories)

            # Update metrics
            if metrics:
                metrics.optimized_sql = optimized_sql
                metrics.complete()
                self.metrics_collector.record(metrics)

            return optimized_sql

        except Exception as e:
            logger.error(f"Optimization error for query {query_id}: {e}")

            if metrics:
                metrics.error = str(e)
                metrics.complete()
                if self.metrics_collector:
                    self.metrics_collector.record(metrics)

            # Return original SQL on error
            return sql

    def _apply_rules(
        self,
        sql: str,
        metrics: Optional[OptimizationMetrics],
        categories: Optional[List[str]] = None,
    ) -> str:
        """
        Apply optimization rules with chaining.

        Rules are applied iteratively until no more transformations occur
        or max_iterations is reached.

        Args:
            sql: SQL query
            metrics: OptimizationMetrics instance
            categories: Optional category filter

        Returns:
            Optimized SQL
        """
        current_sql = sql
        iteration = 0
        total_transformations = 0

        while iteration < self.max_iterations:
            iteration += 1
            iteration_transformations = 0

            # Get applicable rules
            rules = self._get_applicable_rules(categories)

            # Apply each rule
            for rule in rules:
                before_sql = current_sql

                # Try to apply rule
                transformed_sql, transformation_metadata = rule.transform(current_sql)

                # Check if transformation occurred
                if transformed_sql != before_sql:
                    iteration_transformations += 1
                    total_transformations += 1

                    # Log transformation
                    if self.log_transformations:
                        logger.info(
                            f"Applied rule '{rule.name}' (iteration {iteration}): "
                            f"{len(before_sql)} -> {len(transformed_sql)} chars"
                        )
                        logger.debug(f"Before: {before_sql[:100]}...")
                        logger.debug(f"After:  {transformed_sql[:100]}...")

                    # Record in metrics
                    if metrics and transformation_metadata:
                        metrics.add_transformation(
                            rule_name=rule.name,
                            before=before_sql,
                            after=transformed_sql,
                            metadata=transformation_metadata,
                        )

                    # Update current SQL
                    current_sql = transformed_sql

            # If no transformations in this iteration, we're done
            if iteration_transformations == 0:
                if self.log_transformations:
                    logger.info(
                        f"Optimization complete after {iteration} iterations, "
                        f"{total_transformations} total transformations"
                    )
                break

            if self.log_transformations:
                logger.info(
                    f"Iteration {iteration}: {iteration_transformations} transformations"
                )

        return current_sql

    def _get_applicable_rules(
        self,
        categories: Optional[List[str]] = None,
    ) -> List[OptimizationRule]:
        """
        Get applicable rules, optionally filtered by category.

        Args:
            categories: Optional list of categories to include

        Returns:
            List of enabled rules sorted by priority
        """
        if categories:
            rules = []
            for category in categories:
                rules.extend(self.registry.get_rules(category=category, enabled_only=True))
            return sorted(rules, key=lambda r: r.priority)
        else:
            return self.registry.get_rules(enabled_only=True)

    def enable(self):
        """Enable optimizer."""
        self.enabled = True
        if self.log_transformations:
            logger.info("Optimizer enabled")

    def disable(self):
        """Disable optimizer."""
        self.enabled = False
        if self.log_transformations:
            logger.info("Optimizer disabled")

    def toggle(self) -> bool:
        """
        Toggle optimizer on/off.

        Returns:
            New enabled state
        """
        self.enabled = not self.enabled
        if self.log_transformations:
            logger.info(f"Optimizer {'enabled' if self.enabled else 'disabled'}")
        return self.enabled

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.

        Returns:
            Dictionary with optimizer stats
        """
        stats = {
            "enabled": self.enabled,
            "track_metrics": self.track_metrics,
            "log_transformations": self.log_transformations,
            "max_iterations": self.max_iterations,
            "registered_rules": len(self.registry),
            "enabled_rules": len(self.registry.get_rules(enabled_only=True)),
        }

        if self.metrics_collector:
            stats.update(self.metrics_collector.get_stats())
            stats["rule_applications"] = self.metrics_collector.get_rule_stats()

        return stats

    def get_recent_metrics(self, limit: int = 10) -> List[OptimizationMetrics]:
        """
        Get recent optimization metrics.

        Args:
            limit: Number of recent metrics to return

        Returns:
            List of OptimizationMetrics
        """
        if self.metrics_collector:
            return self.metrics_collector.get_recent(limit)
        return []

    def clear_metrics(self):
        """Clear all collected metrics."""
        if self.metrics_collector:
            self.metrics_collector.clear()
            if self.log_transformations:
                logger.info("Metrics cleared")

    def reset_rule_stats(self):
        """Reset statistics for all rules."""
        self.registry.reset_all_stats()
        if self.log_transformations:
            logger.info("Rule statistics reset")

    def __repr__(self) -> str:
        return (
            f"QueryOptimizer(enabled={self.enabled}, "
            f"rules={len(self.registry)}, "
            f"optimizations={self.metrics_collector.total_optimizations if self.metrics_collector else 0})"
        )


__all__ = ["QueryOptimizer"]
