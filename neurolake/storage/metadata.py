"""
Table Metadata Management

Track table metadata, schema, partitions, and history.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class TableMetadata:
    """
    Table metadata including schema, partitions, and properties.

    Example:
        metadata = TableMetadata(
            name="users",
            schema={"id": "bigint", "name": "string", "date": "date"},
            partition_columns=["date"],
            location="/data/lake/users",
            created_at=datetime.now()
        )
    """
    name: str
    schema: Dict[str, str]  # Column name -> type
    partition_columns: List[str] = field(default_factory=list)
    location: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Delta Lake specific
    version: int = 0
    format: str = "delta"
    min_reader_version: int = 1
    min_writer_version: int = 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableMetadata":
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "TableMetadata":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, path: Path):
        """Save metadata to file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: Path) -> "TableMetadata":
        """Load metadata from file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())


@dataclass
class TableHistory:
    """
    Table version history entry.

    Tracks changes to the table over time.
    """
    version: int
    timestamp: datetime
    operation: str  # CREATE, WRITE, MERGE, OPTIMIZE, etc.
    mode: Optional[str] = None  # append, overwrite, etc.
    rows_added: int = 0
    rows_deleted: int = 0
    rows_updated: int = 0
    files_added: int = 0
    files_removed: int = 0
    size_bytes: int = 0
    partition_values: Optional[Dict[str, Any]] = None
    operation_params: Dict[str, Any] = field(default_factory=dict)
    user: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableHistory":
        """Create from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class TableStatistics:
    """
    Table statistics for query optimization.

    Tracks row counts, file counts, and data distribution.
    """
    table_name: str
    total_rows: int = 0
    total_files: int = 0
    total_size_bytes: int = 0
    avg_file_size_bytes: int = 0
    min_file_size_bytes: int = 0
    max_file_size_bytes: int = 0
    partition_count: int = 0
    column_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data


__all__ = [
    "TableMetadata",
    "TableHistory",
    "TableStatistics",
]
