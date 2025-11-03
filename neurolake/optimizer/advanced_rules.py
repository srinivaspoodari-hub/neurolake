"""
Advanced Optimization Rules

Collection of advanced SQL optimization rules for query performance.
"""

import re
from typing import Dict, Any, Tuple, List, Optional

from neurolake.optimizer.rules import OptimizationRule


class PredicatePushdownRule(OptimizationRule):
    """
    Push predicates into subqueries to reduce intermediate result size.

    Pushes WHERE conditions into subqueries when the predicate only references
    columns from the subquery.

    Example:
        Before:
            SELECT * FROM (
                SELECT * FROM users
            ) u WHERE u.age > 18

        After:
            SELECT * FROM (
                SELECT * FROM users WHERE age > 18
            ) u
    """

    def __init__(self):
        super().__init__(
            name="predicate_pushdown",
            description="Push predicates into subqueries",
            category="performance",
            priority=5,
        )

    def matches(self, sql: str) -> bool:
        """Check if there's a subquery with external WHERE clause."""
        # Look for pattern: (SELECT ... FROM ...) alias WHERE
        pattern = r'\(\s*SELECT\s+.*?\s+FROM\s+.*?\)\s+\w+\s+WHERE\s+'
        return bool(re.search(pattern, sql, re.IGNORECASE | re.DOTALL))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Push predicates into subquery."""
        original_sql = sql

        # Pattern to match: (SELECT ... FROM table) alias WHERE condition
        pattern = (
            r'\(\s*SELECT\s+(.*?)\s+FROM\s+(.*?)\)\s+'
            r'(\w+)\s+WHERE\s+([\w.]+\s*[<>=!]+\s*[^\s]+)'
        )

        def push_predicate(match):
            select_cols = match.group(1).strip()
            from_clause = match.group(2).strip()
            alias = match.group(3)
            predicate = match.group(4).strip()

            # Remove alias prefix from predicate if present
            predicate_clean = re.sub(rf'\b{alias}\.', '', predicate)

            # Check if FROM clause already has WHERE
            if re.search(r'\bWHERE\b', from_clause, re.IGNORECASE):
                # Add to existing WHERE with AND
                new_from = re.sub(
                    r'(\bWHERE\b)',
                    rf'\1 {predicate_clean} AND',
                    from_clause,
                    flags=re.IGNORECASE
                )
            else:
                # Add new WHERE clause
                new_from = f"{from_clause} WHERE {predicate_clean}"

            # Return subquery without external WHERE
            return f"(SELECT {select_cols} FROM {new_from}) {alias}"

        optimized_sql = re.sub(
            pattern,
            push_predicate,
            sql,
            flags=re.IGNORECASE | re.DOTALL
        )

        # Clean up any remaining WHERE at the end
        optimized_sql = re.sub(r'\s+WHERE\s*$', '', optimized_sql, flags=re.IGNORECASE)

        metadata = {
            "transformation": "Pushed predicate into subquery",
            "original_length": len(original_sql),
            "optimized_length": len(optimized_sql),
        }

        return optimized_sql, metadata


class ProjectionPruningRule(OptimizationRule):
    """
    Remove unused columns from SELECT statements.

    Prunes columns from subqueries that are not used in the outer query.

    Example:
        Before:
            SELECT id, name FROM (
                SELECT id, name, age, city FROM users
            ) u

        After:
            SELECT id, name FROM (
                SELECT id, name FROM users
            ) u
    """

    def __init__(self):
        super().__init__(
            name="projection_pruning",
            description="Remove unused columns from subqueries",
            category="performance",
            priority=8,
        )

    def matches(self, sql: str) -> bool:
        """Check if there's a subquery with potentially unused columns."""
        # Look for SELECT ... FROM (SELECT ... FROM ...)
        pattern = r'SELECT\s+.*?\s+FROM\s+\(\s*SELECT\s+.*?\s+FROM'
        return bool(re.search(pattern, sql, re.IGNORECASE | re.DOTALL))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Prune unused columns from subquery."""
        original_sql = sql

        # For simple cases: SELECT cols FROM (SELECT * FROM table) alias
        # Convert to: SELECT cols FROM table
        pattern = (
            r'SELECT\s+([\w\s,]+)\s+FROM\s+'
            r'\(\s*SELECT\s+\*\s+FROM\s+([\w.]+)\s*\)\s+\w+'
        )

        def simplify_projection(match):
            outer_cols = match.group(1).strip()
            table_name = match.group(2).strip()

            return f"SELECT {outer_cols} FROM {table_name}"

        optimized_sql = re.sub(
            pattern,
            simplify_projection,
            sql,
            flags=re.IGNORECASE | re.DOTALL,
            count=1
        )

        metadata = {
            "transformation": "Pruned unused columns from subquery",
            "original_length": len(original_sql),
            "optimized_length": len(optimized_sql),
            "simplified": optimized_sql != original_sql,
        }

        return optimized_sql, metadata


class ConstantFoldingRule(OptimizationRule):
    """
    Evaluate constant expressions at optimization time.

    Evaluates arithmetic and string operations with constants.

    Example:
        Before:
            SELECT * FROM users WHERE age > 10 + 8

        After:
            SELECT * FROM users WHERE age > 18
    """

    def __init__(self):
        super().__init__(
            name="constant_folding",
            description="Evaluate constant expressions",
            category="optimization",
            priority=12,
        )

    def matches(self, sql: str) -> bool:
        """Check for constant arithmetic expressions."""
        # Look for patterns like: number + number, number - number, etc.
        patterns = [
            r'\b\d+\s*[\+\-\*/]\s*\d+\b',  # Arithmetic
            r"'[^']*'\s*\|\|\s*'[^']*'",   # String concatenation
        ]
        return any(re.search(p, sql) for p in patterns)

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Fold constant expressions."""
        original_sql = sql
        folded_expressions = []

        # Fold arithmetic expressions
        def fold_arithmetic(match):
            expr = match.group(0)
            try:
                # Safely evaluate arithmetic expression
                result = eval(expr)
                folded_expressions.append(f"{expr} -> {result}")
                return str(result)
            except:
                return expr

        optimized_sql = re.sub(
            r'\b\d+\s*[\+\-\*/]\s*\d+\b',
            fold_arithmetic,
            sql
        )

        # Fold string concatenation (|| in SQL)
        def fold_concat(match):
            expr = match.group(0)
            # Extract strings and concatenate
            strings = re.findall(r"'([^']*)'", expr)
            if strings:
                result = ''.join(strings)
                folded_expressions.append(f"{expr} -> '{result}'")
                return f"'{result}'"
            return expr

        optimized_sql = re.sub(
            r"'[^']*'\s*\|\|\s*'[^']*'",
            fold_concat,
            optimized_sql
        )

        metadata = {
            "transformation": "Folded constant expressions",
            "expressions_folded": len(folded_expressions),
            "details": folded_expressions,
        }

        return optimized_sql, metadata


class RedundantSubqueryRule(OptimizationRule):
    """
    Remove unnecessary subqueries.

    Eliminates subqueries that don't add value (no aggregation, no filtering, etc.).

    Example:
        Before:
            SELECT * FROM (SELECT * FROM users) u

        After:
            SELECT * FROM users u
    """

    def __init__(self):
        super().__init__(
            name="remove_redundant_subquery",
            description="Remove unnecessary subqueries",
            category="simplification",
            priority=6,
        )

    def matches(self, sql: str) -> bool:
        """Check for redundant subqueries."""
        # Look for SELECT * FROM (SELECT * FROM table)
        pattern = r'SELECT\s+\*\s+FROM\s+\(\s*SELECT\s+\*\s+FROM\s+[\w.]+\s*\)'
        return bool(re.search(pattern, sql, re.IGNORECASE | re.DOTALL))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Remove redundant subquery."""
        original_sql = sql

        # Pattern: SELECT * FROM (SELECT * FROM table) alias
        pattern = (
            r'SELECT\s+\*\s+FROM\s+'
            r'\(\s*SELECT\s+\*\s+FROM\s+([\w.]+)\s*\)\s+(\w+)'
        )

        def simplify_subquery(match):
            table_name = match.group(1)
            alias = match.group(2)

            return f"SELECT * FROM {table_name} {alias}"

        optimized_sql = re.sub(
            pattern,
            simplify_subquery,
            sql,
            flags=re.IGNORECASE | re.DOTALL,
            count=1
        )

        metadata = {
            "transformation": "Removed redundant subquery",
            "original_length": len(original_sql),
            "optimized_length": len(optimized_sql),
        }

        return optimized_sql, metadata


class JoinReorderingRule(OptimizationRule):
    """
    Reorder joins for better performance (simplified version).

    In a real implementation, this would use statistics and cost estimation.
    This simplified version provides basic join reordering suggestions.

    Example:
        Before:
            SELECT * FROM large_table l
            JOIN small_table s ON l.id = s.id

        Suggestion:
            Consider joining smaller tables first for better performance
    """

    def __init__(self):
        super().__init__(
            name="join_reordering",
            description="Suggest join reordering for performance",
            category="performance",
            priority=15,
            enabled=False,  # Disabled by default (needs statistics)
        )

    def matches(self, sql: str) -> bool:
        """Check for JOIN operations."""
        return bool(re.search(r'\bJOIN\b', sql, re.IGNORECASE))

    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """Analyze joins and provide suggestions."""
        # Count number of joins
        joins = re.findall(r'\bJOIN\b', sql, re.IGNORECASE)
        join_count = len(joins)

        # Check for specific patterns that might be problematic
        suggestions = []

        # Check for cross joins (no ON clause immediately after JOIN)
        if re.search(r'\bJOIN\s+\w+\s+(?!ON)', sql, re.IGNORECASE):
            suggestions.append("Possible CROSS JOIN detected - ensure ON clause is present")

        # Check for multiple joins
        if join_count > 3:
            suggestions.append(
                f"Multiple joins ({join_count}) detected - consider join order and indexes"
            )

        metadata = {
            "transformation": "Join analysis",
            "join_count": join_count,
            "suggestions": suggestions,
            "note": "Full join reordering requires table statistics",
            "transformed": False,
        }

        # Don't transform, just analyze
        return sql, metadata


def register_advanced_rules(registry):
    """
    Register all advanced optimization rules.

    Args:
        registry: RuleRegistry instance
    """
    rules = [
        PredicatePushdownRule(),
        ProjectionPruningRule(),
        ConstantFoldingRule(),
        RedundantSubqueryRule(),
        JoinReorderingRule(),
    ]

    for rule in rules:
        try:
            registry.register(rule)
        except ValueError:
            # Rule already registered
            pass


__all__ = [
    "PredicatePushdownRule",
    "ProjectionPruningRule",
    "ConstantFoldingRule",
    "RedundantSubqueryRule",
    "JoinReorderingRule",
    "register_advanced_rules",
]
