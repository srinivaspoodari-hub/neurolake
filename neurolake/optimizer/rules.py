"""
Optimization Rules and Registry

Defines the base interface for optimization rules and provides a registry
for managing and applying rules.
"""

from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
import re
from datetime import datetime


class OptimizationRule(ABC):
    """
    Base class for SQL optimization rules.

    Each rule implements a specific transformation that can improve
    query performance, readability, or efficiency.

    Attributes:
        name: Unique rule identifier
        description: Human-readable description
        category: Rule category (e.g., "predicate", "join", "projection")
        priority: Execution priority (lower = higher priority)
        enabled: Whether rule is active
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: str = "general",
        priority: int = 100,
        enabled: bool = True,
    ):
        """
        Initialize optimization rule.

        Args:
            name: Unique rule identifier
            description: Human-readable description
            category: Rule category
            priority: Execution priority (lower = runs first)
            enabled: Whether rule is active
        """
        self.name = name
        self.description = description
        self.category = category
        self.priority = priority
        self.enabled = enabled
        self.application_count = 0
        self.created_at = datetime.now()

    @abstractmethod
    def matches(self, sql: str) -> bool:
        """
        Check if rule applies to given SQL.

        Args:
            sql: SQL query to check

        Returns:
            True if rule can be applied
        """
        pass

    @abstractmethod
    def apply(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """
        Apply optimization rule to SQL.

        Args:
            sql: Original SQL query

        Returns:
            Tuple of (optimized_sql, transformation_metadata)
            - optimized_sql: Transformed SQL
            - transformation_metadata: Dict with transformation details
        """
        pass

    def can_apply(self, sql: str) -> bool:
        """
        Check if rule is enabled and matches SQL.

        Args:
            sql: SQL query

        Returns:
            True if rule should be applied
        """
        return self.enabled and self.matches(sql)

    def transform(self, sql: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Transform SQL if rule applies.

        Args:
            sql: Original SQL

        Returns:
            Tuple of (sql, metadata)
            - If rule applies: (transformed_sql, metadata)
            - If rule doesn't apply: (original_sql, None)
        """
        if not self.can_apply(sql):
            return sql, None

        optimized_sql, metadata = self.apply(sql)
        self.application_count += 1

        # Add rule metadata
        metadata["rule_name"] = self.name
        metadata["rule_category"] = self.category
        metadata["applied_at"] = datetime.now().isoformat()

        return optimized_sql, metadata

    def reset_stats(self):
        """Reset application statistics."""
        self.application_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get rule statistics."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "enabled": self.enabled,
            "application_count": self.application_count,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"OptimizationRule(name='{self.name}', category='{self.category}', priority={self.priority})"


class RuleRegistry:
    """
    Registry for managing optimization rules.

    Provides centralized management of optimization rules with support for:
    - Rule registration and retrieval
    - Priority-based ordering
    - Category filtering
    - Enable/disable individual rules
    """

    def __init__(self):
        """Initialize rule registry."""
        self.rules: Dict[str, OptimizationRule] = {}
        self._sorted_rules: Optional[List[OptimizationRule]] = None

    def register(self, rule: OptimizationRule):
        """
        Register an optimization rule.

        Args:
            rule: OptimizationRule instance

        Raises:
            ValueError: If rule with same name already exists
        """
        if rule.name in self.rules:
            raise ValueError(f"Rule '{rule.name}' already registered")

        self.rules[rule.name] = rule
        self._sorted_rules = None  # Invalidate cache

    def unregister(self, name: str):
        """
        Unregister a rule.

        Args:
            name: Rule name
        """
        self.rules.pop(name, None)
        self._sorted_rules = None

    def get(self, name: str) -> Optional[OptimizationRule]:
        """
        Get rule by name.

        Args:
            name: Rule name

        Returns:
            OptimizationRule or None
        """
        return self.rules.get(name)

    def get_rules(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[OptimizationRule]:
        """
        Get rules, optionally filtered.

        Args:
            category: Filter by category (None = all)
            enabled_only: Only return enabled rules

        Returns:
            List of rules sorted by priority
        """
        # Get sorted rules (cached)
        if self._sorted_rules is None:
            self._sorted_rules = sorted(
                self.rules.values(),
                key=lambda r: r.priority
            )

        rules = self._sorted_rules

        # Apply filters
        if category:
            rules = [r for r in rules if r.category == category]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def get_categories(self) -> List[str]:
        """Get all rule categories."""
        return sorted(set(r.category for r in self.rules.values()))

    def enable_rule(self, name: str):
        """Enable a rule."""
        rule = self.get(name)
        if rule:
            rule.enabled = True

    def disable_rule(self, name: str):
        """Disable a rule."""
        rule = self.get(name)
        if rule:
            rule.enabled = False

    def enable_category(self, category: str):
        """Enable all rules in a category."""
        for rule in self.rules.values():
            if rule.category == category:
                rule.enabled = True

    def disable_category(self, category: str):
        """Disable all rules in a category."""
        for rule in self.rules.values():
            if rule.category == category:
                rule.enabled = False

    def reset_all_stats(self):
        """Reset statistics for all rules."""
        for rule in self.rules.values():
            rule.reset_stats()

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all rules."""
        return [rule.get_stats() for rule in self.rules.values()]

    def list_rules(self) -> List[str]:
        """Get list of all rule names."""
        return list(self.rules.keys())

    def __len__(self) -> int:
        return len(self.rules)

    def __repr__(self) -> str:
        return f"RuleRegistry(rules={len(self.rules)})"


# Global registry
_global_registry = RuleRegistry()


def get_rule_registry() -> RuleRegistry:
    """Get the global rule registry."""
    return _global_registry


__all__ = [
    "OptimizationRule",
    "RuleRegistry",
    "get_rule_registry",
]
