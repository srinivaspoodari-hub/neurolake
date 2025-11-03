"""
Query Template System and Prepared Statements

Provides reusable query templates with named placeholders and prepared statement support.
"""

from typing import Dict, Any, Optional, List
import re
from datetime import datetime


class QueryTemplate:
    """
    Reusable SQL query template with named placeholders.

    Templates allow defining SQL queries once and reusing them with different parameters.
    Supports both simple substitution and parameterized queries.

    Example:
        template = QueryTemplate(
            name="get_user_orders",
            sql="SELECT * FROM orders WHERE user_id = :user_id AND date > :min_date",
            description="Get all orders for a user after a date"
        )

        result = template.render(user_id=123, min_date="2024-01-01")
    """

    def __init__(
        self,
        name: str,
        sql: str,
        description: Optional[str] = None,
        default_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize query template.

        Args:
            name: Template name/identifier
            sql: SQL query with :param placeholders
            description: Optional description of the template
            default_params: Default parameter values
        """
        self.name = name
        self.sql = sql
        self.description = description
        self.default_params = default_params or {}
        self.created_at = datetime.now()
        self.execution_count = 0

        # Extract required parameters
        self.required_params = set(re.findall(r':(\w+)', sql))

    def render(self, **params) -> str:
        """
        Render template with parameters.

        Args:
            **params: Parameter values

        Returns:
            SQL query with parameters substituted

        Raises:
            ValueError: If required parameters are missing
        """
        # Merge default params with provided params
        all_params = {**self.default_params, **params}

        # Check for missing required parameters
        missing = self.required_params - set(all_params.keys())
        if missing:
            raise ValueError(
                f"Template '{self.name}' missing required parameters: {', '.join(missing)}"
            )

        # Return SQL with params (will be substituted by engine)
        self.execution_count += 1
        return self.sql

    def get_params(self, **params) -> Dict[str, Any]:
        """
        Get merged parameters for execution.

        Args:
            **params: Parameter values

        Returns:
            Dictionary of all parameters (defaults + provided)
        """
        return {**self.default_params, **params}

    def validate_params(self, **params) -> bool:
        """
        Validate that all required parameters are provided.

        Args:
            **params: Parameter values

        Returns:
            True if all required parameters are present
        """
        all_params = {**self.default_params, **params}
        return self.required_params.issubset(set(all_params.keys()))

    def __repr__(self) -> str:
        return f"QueryTemplate(name='{self.name}', params={list(self.required_params)})"


class PreparedStatement:
    """
    Prepared statement for repeated execution with different parameters.

    Similar to QueryTemplate but optimized for repeated execution with
    parameter validation and execution tracking.

    Example:
        stmt = PreparedStatement(
            "SELECT * FROM users WHERE id = :user_id",
            name="get_user_by_id"
        )

        # Execute multiple times
        result1 = stmt.execute(engine, user_id=123)
        result2 = stmt.execute(engine, user_id=456)
    """

    def __init__(
        self,
        sql: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize prepared statement.

        Args:
            sql: SQL query with :param placeholders
            name: Optional statement name
            description: Optional description
        """
        self.sql = sql
        self.name = name or f"stmt_{id(self)}"
        self.description = description
        self.created_at = datetime.now()
        self.execution_count = 0
        self.last_execution = None
        self.execution_history: List[Dict[str, Any]] = []

        # Extract required parameters
        self.required_params = set(re.findall(r':(\w+)', sql))

    def execute(
        self,
        engine,
        return_format: str = "dataframe",
        **params
    ):
        """
        Execute prepared statement with parameters.

        Args:
            engine: NeuroLakeEngine instance
            return_format: Result format
            **params: Parameter values

        Returns:
            Query results

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate parameters
        missing = self.required_params - set(params.keys())
        if missing:
            raise ValueError(
                f"Prepared statement '{self.name}' missing required parameters: {', '.join(missing)}"
            )

        # Execute query
        start_time = datetime.now()
        result = engine.execute_sql(
            self.sql,
            params=params,
            return_format=return_format
        )

        # Track execution
        self.execution_count += 1
        self.last_execution = start_time
        self.execution_history.append({
            "timestamp": start_time,
            "params": params.copy(),
            "row_count": len(result) if hasattr(result, "__len__") else None,
        })

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution stats
        """
        return {
            "name": self.name,
            "sql": self.sql,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution,
            "created_at": self.created_at,
            "required_params": list(self.required_params),
        }

    def __repr__(self) -> str:
        return f"PreparedStatement(name='{self.name}', executions={self.execution_count})"


class TemplateRegistry:
    """
    Registry for managing query templates.

    Provides centralized storage and retrieval of query templates.
    """

    def __init__(self):
        self.templates: Dict[str, QueryTemplate] = {}

    def register(self, template: QueryTemplate):
        """Register a template."""
        self.templates[template.name] = template

    def get(self, name: str) -> Optional[QueryTemplate]:
        """Get template by name."""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List all template names."""
        return list(self.templates.keys())

    def remove(self, name: str):
        """Remove template by name."""
        self.templates.pop(name, None)

    def create_and_register(
        self,
        name: str,
        sql: str,
        description: Optional[str] = None,
        default_params: Optional[Dict[str, Any]] = None,
    ) -> QueryTemplate:
        """Create and register a template in one step."""
        template = QueryTemplate(name, sql, description, default_params)
        self.register(template)
        return template

    def __repr__(self) -> str:
        return f"TemplateRegistry(templates={len(self.templates)})"


# Global registry
_global_registry = TemplateRegistry()


def get_template_registry() -> TemplateRegistry:
    """Get the global template registry."""
    return _global_registry


__all__ = [
    "QueryTemplate",
    "PreparedStatement",
    "TemplateRegistry",
    "get_template_registry",
]
