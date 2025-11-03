"""
NeuroLake Query Optimizer

SQL query optimization framework with rule-based transformations.

Example:
    from neurolake.optimizer import QueryOptimizer, OptimizationRule

    optimizer = QueryOptimizer(enabled=True)
    optimized_sql = optimizer.optimize("SELECT * FROM users WHERE 1=1")
"""

from neurolake.optimizer.optimizer import QueryOptimizer
from neurolake.optimizer.rules import (
    OptimizationRule,
    RuleRegistry,
    get_rule_registry,
)
from neurolake.optimizer.metrics import OptimizationMetrics
from neurolake.optimizer.builtin_rules import register_builtin_rules
from neurolake.optimizer.advanced_rules import register_advanced_rules

__all__ = [
    "QueryOptimizer",
    "OptimizationRule",
    "RuleRegistry",
    "get_rule_registry",
    "OptimizationMetrics",
    "register_builtin_rules",
    "register_advanced_rules",
]
