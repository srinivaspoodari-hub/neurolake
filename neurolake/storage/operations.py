"""
Storage Operations

Define operation modes and classes for Delta Lake operations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


class WriteMode(Enum):
    """Write modes for table operations."""
    APPEND = "append"
    OVERWRITE = "overwrite"
    ERROR_IF_EXISTS = "error"
    IGNORE = "ignore"


@dataclass
class MergeOperation:
    """
    MERGE/UPSERT operation configuration.

    Example:
        merge = MergeOperation(
            source_alias="updates",
            target_alias="target",
            merge_condition="target.id = updates.id",
            when_matched_update={"status": "updates.status"},
            when_not_matched_insert={"id": "updates.id", "status": "updates.status"}
        )
    """
    source_alias: str = "source"
    target_alias: str = "target"
    merge_condition: str = ""
    when_matched_update: Optional[Dict[str, str]] = None
    when_matched_delete: Optional[str] = None  # Condition for delete
    when_not_matched_insert: Optional[Dict[str, str]] = None


@dataclass
class OptimizeOperation:
    """
    OPTIMIZE operation configuration.

    Example:
        optimize = OptimizeOperation(
            z_order_by=["user_id", "timestamp"],
            where="date >= '2025-01-01'",
            max_file_size_mb=128
        )
    """
    z_order_by: Optional[List[str]] = None
    where: Optional[str] = None
    max_file_size_mb: int = 128
    min_file_size_mb: int = 8


@dataclass
class VacuumOperation:
    """
    VACUUM operation configuration.

    Example:
        vacuum = VacuumOperation(
            retention_hours=168,  # 7 days
            dry_run=True
        )
    """
    retention_hours: int = 168  # 7 days default
    dry_run: bool = False


__all__ = [
    "WriteMode",
    "MergeOperation",
    "OptimizeOperation",
    "VacuumOperation",
]
