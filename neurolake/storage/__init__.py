"""
NeuroLake Storage Module

NCF-based storage management with time travel, ACID transactions, and optimizations.

Example:
    from neurolake.storage import NCFStorageManager

    storage = NCFStorageManager(base_path="/data/lake")

    # Create table
    storage.create_table("users", schema=schema, partition_by=["date"])

    # Write data
    storage.write_table("users", data, mode="append")

    # Read data
    data = storage.read_table("users")

    # Time travel
    data_v1 = storage.read_table("users", version=1)
    data_ts = storage.read_table("users", timestamp="2025-01-01")

    # Optimize
    storage.optimize("users", z_order_by=["user_id"])
"""

from neurolake.storage.manager import NCFStorageManager
from neurolake.storage.metadata import TableMetadata, TableHistory
from neurolake.storage.operations import (
    WriteMode,
    MergeOperation,
    OptimizeOperation,
    VacuumOperation,
)

__all__ = [
    "NCFStorageManager",
    "TableMetadata",
    "TableHistory",
    "WriteMode",
    "MergeOperation",
    "OptimizeOperation",
    "VacuumOperation",
]
