"""
Built-in Optimization Rules

Collection of common SQL optimization rules.
"""

import re
from typing import Dict, Any, Tuple

from neurolake.optimizer.rules import OptimizationRule


class RemoveRedundantPredicatesRule(OptimizationRule):
    """
    Remove always-true predicates like WHERE 1=1.

    Example:
        SELECT * FROM users WHERE 1=1 AND age > 18
        -> SELECT * FROM users WHERE age > 18
    """

    def __init__(self):
        super().__init__(
            name="remove_redundant_predicates",
            description="Remove always-true predicates (1=1, TRUE, etc.)",
            category="predicate",
            priority=10,
        )

    def matches(self, sql: str) -> bool:
        """Check if SQL contains redundant predicates."""
        patterns = [
            r'\b1\s*=\s*1\b',
            r'\bTRUE\b',
            r'\b0\s*=\s*0\b',
        ]
        return any(re.search(p, sql, re.IGNORECASE) for p in patterns)

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Remove redundant predicates."""
        original_sql = sql
        transformations = []

        # Remove 1=1
        if re.search(r'\b1\s*=\s*1\b', sql, re.IGNORECASE):
            sql = re.sub(r'\bWHERE\s+1\s*=\s*1\s+AND\s+', 'WHERE ', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bAND\s+1\s*=\s*1\b', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bWHERE\s+1\s*=\s*1\b', '', sql, flags=re.IGNORECASE)
            transformations.append("Removed 1=1")

        # Remove TRUE
        if re.search(r'\bTRUE\b', sql, re.IGNORECASE):
            sql = re.sub(r'\bWHERE\s+TRUE\s+AND\s+', 'WHERE ', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bAND\s+TRUE\b', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bWHERE\s+TRUE\b', '', sql, flags=re.IGNORECASE)
            transformations.append("Removed TRUE")

        # Clean up extra whitespace
        sql = re.sub(r'\s+', ' ', sql).strip()

        metadata = {
            "transformations": transformations,
            "original_length": len(original_sql),
            "optimized_length": len(sql),
        }

        return sql, metadata


class RemoveSelectStarRule(OptimizationRule):
    """
    Warning for SELECT * usage (doesn't transform, just warns).

    SELECT * can cause issues with:
    - Performance (unnecessary columns)
    - Schema changes
    - Network overhead
    """

    def __init__(self):
        super().__init__(
            name="warn_select_star",
            description="Warn about SELECT * usage",
            category="projection",
            priority=50,
            enabled=False,  # Disabled by default (warning only)
        )

    def matches(self, sql: str) -> bool:
        """Check for SELECT *."""
        return bool(re.search(r'\bSELECT\s+\*\b', sql, re.IGNORECASE))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Just log warning, don't transform."""
        metadata = {
            "warning": "SELECT * detected - consider specifying columns explicitly",
            "transformed": False,
        }
        return sql, metadata


class SimplifyDoubleNegationRule(OptimizationRule):
    """
    Simplify double negation (NOT NOT x -> x).

    Example:
        SELECT * FROM users WHERE NOT (NOT active)
        -> SELECT * FROM users WHERE active
    """

    def __init__(self):
        super().__init__(
            name="simplify_double_negation",
            description="Simplify NOT (NOT x) to x",
            category="predicate",
            priority=20,
        )

    def matches(self, sql: str) -> bool:
        """Check for NOT (NOT ...)."""
        return bool(re.search(r'\bNOT\s+\(\s*NOT\s+', sql, re.IGNORECASE))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Simplify double negation."""
        original_sql = sql

        # Simple case: NOT (NOT column)
        sql = re.sub(
            r'\bNOT\s+\(\s*NOT\s+(\w+)\s*\)',
            r'\1',
            sql,
            flags=re.IGNORECASE
        )

        metadata = {
            "transformation": "Simplified double negation",
            "original_length": len(original_sql),
            "optimized_length": len(sql),
        }

        return sql, metadata


class RemoveRedundantDistinctRule(OptimizationRule):
    """
    Remove DISTINCT when there's already a PRIMARY KEY or UNIQUE constraint.

    Note: This is a simplified version - in production, would need
    schema information to verify uniqueness.
    """

    def __init__(self):
        super().__init__(
            name="remove_redundant_distinct",
            description="Remove DISTINCT when selecting unique columns",
            category="projection",
            priority=30,
            enabled=False,  # Disabled by default (needs schema info)
        )

    def matches(self, sql: str) -> bool:
        """Check for DISTINCT."""
        return bool(re.search(r'\bSELECT\s+DISTINCT\b', sql, re.IGNORECASE))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Log warning about DISTINCT usage."""
        metadata = {
            "warning": "DISTINCT detected - verify if necessary with schema constraints",
            "transformed": False,
        }
        return sql, metadata


class PushDownPredicatesRule(OptimizationRule):
    """
    Push WHERE predicates closer to table scans.

    Example (simplified):
        SELECT * FROM (SELECT * FROM users) u WHERE u.age > 18
        -> SELECT * FROM (SELECT * FROM users WHERE age > 18) u
    """

    def __init__(self):
        super().__init__(
            name="push_down_predicates",
            description="Push predicates down to subqueries",
            category="predicate",
            priority=40,
            enabled=False,  # Complex rule, disabled by default
        )

    def matches(self, sql: str) -> bool:
        """Check if there are predicates that could be pushed down."""
        # Simplified check
        has_subquery = bool(re.search(r'\(\s*SELECT', sql, re.IGNORECASE))
        has_where = bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))
        return has_subquery and has_where

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Log suggestion (actual implementation would be complex)."""
        metadata = {
            "suggestion": "Consider pushing predicates into subqueries",
            "transformed": False,
        }
        return sql, metadata


def register_builtin_rules(registry):
    """
    Register all built-in optimization rules.

    Args:
        registry: RuleRegistry instance
    """
    rules = [
        RemoveRedundantPredicatesRule(),
        SimplifyDoubleNegationRule(),
        RemoveSelectStarRule(),
        RemoveRedundantDistinctRule(),
        PushDownPredicatesRule(),
    ]

    for rule in rules:
        try:
            registry.register(rule)
        except ValueError:
            # Rule already registered
            pass


__all__ = [
    "RemoveRedundantPredicatesRule",
    "RemoveSelectStarRule",
    "SimplifyDoubleNegationRule",
    "RemoveRedundantDistinctRule",
    "PushDownPredicatesRule",
    "register_builtin_rules",
]
