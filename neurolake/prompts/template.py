"""
Prompt Template System

Versioned, reusable prompt templates with variable substitution.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from string import Template
import json


@dataclass
class PromptVersion:
    """A versioned prompt template."""
    version: str
    template: str
    variables: List[str]
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    performance_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs) -> str:
        """
        Render the template with variables.

        Args:
            **kwargs: Variable values

        Returns:
            Rendered prompt

        Raises:
            ValueError: If required variables are missing
        """
        # Check for missing variables
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Render template
        template = Template(self.template)
        return template.safe_substitute(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "template": self.template,
            "variables": self.variables,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "performance_score": self.performance_score,
            "metadata": self.metadata
        }


class PromptTemplate:
    """
    Versioned prompt template with performance tracking.

    Example:
        template = PromptTemplate(
            name="intent_parser",
            description="Parse user intent from natural language"
        )

        # Add version
        template.add_version(
            version="v1.0",
            template="Parse this query: $user_query",
            variables=["user_query"]
        )

        # Render
        prompt = template.render(user_query="Show me all users")
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        default_version: str = "latest"
    ):
        """
        Initialize prompt template.

        Args:
            name: Template name
            description: Template description
            default_version: Default version to use
        """
        self.name = name
        self.description = description
        self.default_version = default_version
        self.versions: Dict[str, PromptVersion] = {}
        self.performance_history: List[Dict[str, Any]] = []

    def add_version(
        self,
        version: str,
        template: str,
        variables: List[str],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a new version of the prompt.

        Args:
            version: Version identifier
            template: Prompt template string with $variables
            variables: List of required variables
            description: Version description
            metadata: Additional metadata
        """
        prompt_version = PromptVersion(
            version=version,
            template=template,
            variables=variables,
            description=description,
            metadata=metadata or {}
        )

        self.versions[version] = prompt_version

        # Update default to latest
        if self.default_version == "latest":
            self.default_version = version

    def render(
        self,
        version: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Render the prompt template.

        Args:
            version: Version to use (None = default)
            **kwargs: Template variables

        Returns:
            Rendered prompt
        """
        ver = version or self.default_version

        if ver not in self.versions:
            raise ValueError(
                f"Version '{ver}' not found. "
                f"Available versions: {list(self.versions.keys())}"
            )

        return self.versions[ver].render(**kwargs)

    def get_version(self, version: str) -> PromptVersion:
        """Get a specific version."""
        if version not in self.versions:
            raise ValueError(f"Version '{version}' not found")
        return self.versions[version]

    def list_versions(self) -> List[str]:
        """List all versions."""
        return list(self.versions.keys())

    def record_performance(
        self,
        version: str,
        score: float,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Record performance for a version.

        Args:
            version: Version identifier
            score: Performance score (0-1)
            metrics: Additional metrics
        """
        if version not in self.versions:
            raise ValueError(f"Version '{version}' not found")

        self.versions[version].performance_score = score

        self.performance_history.append({
            "version": version,
            "score": score,
            "metrics": metrics or {},
            "timestamp": datetime.now().isoformat()
        })

    def get_best_version(self) -> str:
        """Get the best performing version based on scores."""
        scored_versions = [
            (ver, pv.performance_score)
            for ver, pv in self.versions.items()
            if pv.performance_score is not None
        ]

        if not scored_versions:
            return self.default_version

        return max(scored_versions, key=lambda x: x[1])[0]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "default_version": self.default_version,
            "versions": {
                ver: pv.to_dict()
                for ver, pv in self.versions.items()
            },
            "performance_history": self.performance_history
        }

    def save(self, path: str):
        """Save template to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "PromptTemplate":
        """Load template from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        template = cls(
            name=data["name"],
            description=data["description"],
            default_version=data["default_version"]
        )

        for ver, ver_data in data["versions"].items():
            template.add_version(
                version=ver,
                template=ver_data["template"],
                variables=ver_data["variables"],
                description=ver_data["description"],
                metadata=ver_data["metadata"]
            )

            if ver_data["performance_score"] is not None:
                template.versions[ver].performance_score = ver_data["performance_score"]

        template.performance_history = data.get("performance_history", [])

        return template


__all__ = ["PromptTemplate", "PromptVersion"]
