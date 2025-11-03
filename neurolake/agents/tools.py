"""
Tool Abstraction and Registry

Tools that agents can use to interact with the environment.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Tool(ABC):
    """
    Abstract base class for agent tools.

    Example:
        class QueryTool(Tool):
            def __init__(self):
                super().__init__(
                    name="query",
                    description="Execute SQL queries"
                )

            def execute(self, **kwargs):
                query = kwargs.get("query")
                # Execute query...
                return results
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: Expected parameters
        """
        self.name = name
        self.description = description
        self.parameters = parameters or []

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool output
        """
        pass

    def validate_parameters(self, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        for param in self.parameters:
            if param.get("required", False):
                if param["name"] not in kwargs:
                    raise ValueError(f"Missing required parameter: {param['name']}")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class FunctionTool(Tool):
    """Tool that wraps a Python function."""

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize function tool.

        Args:
            name: Tool name
            description: Tool description
            function: Function to wrap
            parameters: Expected parameters
        """
        super().__init__(name, description, parameters)
        self.function = function

    def execute(self, **kwargs) -> Any:
        """Execute the wrapped function."""
        self.validate_parameters(**kwargs)
        return self.function(**kwargs)


class QueryTool(Tool):
    """Tool for executing queries."""

    def __init__(self, query_engine: Any):
        """
        Initialize query tool.

        Args:
            query_engine: Query engine to use
        """
        super().__init__(
            name="query",
            description="Execute SQL or natural language queries",
            parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "description": "Query to execute",
                    "required": True
                }
            ]
        )
        self.engine = query_engine

    def execute(self, **kwargs) -> Any:
        """Execute a query."""
        self.validate_parameters(**kwargs)
        query = kwargs["query"]
        return self.engine.execute(query)


class AnalyzeTool(Tool):
    """Tool for data analysis."""

    def __init__(self, analyzer: Any):
        """
        Initialize analyze tool.

        Args:
            analyzer: Data analyzer
        """
        super().__init__(
            name="analyze",
            description="Analyze data and generate insights",
            parameters=[
                {
                    "name": "data",
                    "type": "any",
                    "description": "Data to analyze",
                    "required": True
                },
                {
                    "name": "analysis_type",
                    "type": "string",
                    "description": "Type of analysis (trend, summary, anomaly)",
                    "required": False
                }
            ]
        )
        self.analyzer = analyzer

    def execute(self, **kwargs) -> Any:
        """Analyze data."""
        self.validate_parameters(**kwargs)
        data = kwargs["data"]
        analysis_type = kwargs.get("analysis_type", "summary")
        return self.analyzer.analyze(data, analysis_type)


class SearchTool(Tool):
    """Tool for searching information."""

    def __init__(self, search_engine: Any):
        """
        Initialize search tool.

        Args:
            search_engine: Search engine
        """
        super().__init__(
            name="search",
            description="Search for information",
            parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "description": "Search query",
                    "required": True
                },
                {
                    "name": "limit",
                    "type": "integer",
                    "description": "Maximum results",
                    "required": False
                }
            ]
        )
        self.engine = search_engine

    def execute(self, **kwargs) -> Any:
        """Search for information."""
        self.validate_parameters(**kwargs)
        query = kwargs["query"]
        limit = kwargs.get("limit", 10)
        return self.engine.search(query, limit=limit)


class ToolRegistry:
    """
    Registry for managing agent tools.

    Example:
        registry = ToolRegistry()
        registry.register(QueryTool(engine))
        registry.register(AnalyzeTool(analyzer))

        tool = registry.get("query")
        result = tool.execute(query="SELECT * FROM users")
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """
        Register a tool.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str):
        """
        Unregister a tool.

        Args:
            name: Tool name
        """
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered tool: {name}")

    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool or None
        """
        return self.tools.get(name)

    def list(self) -> List[Tool]:
        """
        List all registered tools.

        Returns:
            List of tools
        """
        return list(self.tools.values())

    def list_names(self) -> List[str]:
        """
        List all tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert registry to dictionary."""
        return {
            name: tool.to_dict()
            for name, tool in self.tools.items()
        }


# Global tool registry
_global_registry = ToolRegistry()


def register_tool(tool: Tool):
    """Register a tool in the global registry."""
    _global_registry.register(tool)


def get_tool(name: str) -> Optional[Tool]:
    """Get a tool from the global registry."""
    return _global_registry.get(name)


def list_tools() -> List[Tool]:
    """List all tools in the global registry."""
    return _global_registry.list()


__all__ = [
    "Tool",
    "FunctionTool",
    "QueryTool",
    "AnalyzeTool",
    "SearchTool",
    "ToolRegistry",
    "register_tool",
    "get_tool",
    "list_tools",
]
