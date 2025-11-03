"""
Test Storage Module

Comprehensive tests for Delta Lake storage management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from neurolake.storage import (
    NCFStorageManager,
    TableMetadata,
    TableHistory,
    WriteMode,
    MergeOperation,
    OptimizeOperation,
    VacuumOperation,
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage):
    """Create storage manager."""
    return NCFStorageManager(base_path=temp_storage)


# ===== Test TableMetadata =====

def test_table_metadata_creation():
    """Test metadata creation."""
    metadata = TableMetadata(
        name="users",
        schema={"id": "int64", "name": "string"},
        partition_columns=["date"],
        location="/data/users",
    )

    assert metadata.name == "users"
    assert metadata.schema == {"id": "int64", "name": "string"}
    assert metadata.partition_columns == ["date"]
    assert metadata.version == 0

    print(f"[PASS] Metadata creation: {metadata.name}")


def test_table_metadata_serialization():
    """Test metadata serialization."""
    metadata = TableMetadata(
        name="test",
        schema={"col1": "int64"},
    )

    # To dict
    data = metadata.to_dict()
    assert data["name"] == "test"
    assert "created_at" in data

    # To JSON
    json_str = metadata.to_json()
    assert "test" in json_str

    # From dict
    metadata2 = TableMetadata.from_dict(data)
    assert metadata2.name == metadata.name

    print("[PASS] Metadata serialization")


def test_table_metadata_save_load(temp_storage):
    """Test metadata save and load."""
    metadata = TableMetadata(
        name="test",
        schema={"id": "int64"},
    )

    path = Path(temp_storage) / "test_metadata.json"
    metadata.save(path)

    loaded = TableMetadata.load(path)
    assert loaded.name == metadata.name
    assert loaded.schema == metadata.schema

    print("[PASS] Metadata save/load")


# ===== Test TableHistory =====

def test_table_history_creation():
    """Test history creation."""
    history = TableHistory(
        version=1,
        timestamp=datetime.now(),
        operation="WRITE",
        mode="append",
        rows_added=100,
        files_added=1,
    )

    assert history.version == 1
    assert history.operation == "WRITE"
    assert history.rows_added == 100

    print(f"[PASS] History creation: v{history.version}, {history.operation}")


def test_table_history_serialization():
    """Test history serialization."""
    history = TableHistory(
        version=1,
        timestamp=datetime.now(),
        operation="CREATE",
    )

    # To dict
    data = history.to_dict()
    assert data["version"] == 1

    # From dict
    history2 = TableHistory.from_dict(data)
    assert history2.version == history.version

    print("[PASS] History serialization")


# ===== Test NCFStorageManager =====

def test_storage_manager_creation(temp_storage):
    """Test storage manager initialization."""
    storage = NCFStorageManager(base_path=temp_storage)

    assert storage.base_path == Path(temp_storage)
    assert storage.base_path.exists()

    print(f"[PASS] Storage manager created at {storage.base_path}")


def test_create_table(storage):
    """Test table creation."""
    schema = {
        "id": "int64",
        "name": "string",
        "age": "int32",
    }

    metadata = storage.create_table("users", schema, description="User table")

    assert metadata.name == "users"
    assert metadata.schema == schema
    assert metadata.version == 0

    # Check files exist
    table_path = storage._get_table_path("users")
    assert table_path.exists()
    assert (table_path / "_metadata.json").exists()

    print(f"[PASS] Table created: {metadata.name}")


def test_create_table_with_partitions(storage):
    """Test table creation with partitions."""
    schema = {"id": "int64", "date": "string", "value": "double"}

    metadata = storage.create_table(
        "metrics",
        schema,
        partition_by=["date"],
    )

    assert metadata.partition_columns == ["date"]

    print(f"[PASS] Partitioned table created: {metadata.partition_columns}")


def test_create_table_already_exists(storage):
    """Test creating table that already exists."""
    schema = {"id": "int64"}
    storage.create_table("test", schema)

    # Should raise error
    with pytest.raises(ValueError, match="already exists"):
        storage.create_table("test", schema)

    print("[PASS] Duplicate table creation raises error")


def test_create_table_overwrite(storage):
    """Test overwriting existing table."""
    schema = {"id": "int64"}
    storage.create_table("test_overwrite", schema)

    # Overwrite
    storage.create_table("test_overwrite", schema, overwrite=True)

    metadata = storage.get_metadata("test_overwrite")
    assert metadata.name == "test_overwrite"

    print("[PASS] Table overwrite works")


def test_write_table_append(storage):
    """Test writing data in append mode."""
    schema = {"id": "int64", "name": "string"}
    storage.create_table("users", schema)

    # Write data
    data = {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]}
    history = storage.write_table("users", data, mode="append")

    assert history.operation == "WRITE"
    assert history.mode == "append"
    assert history.rows_added == 3

    # Metadata version should increment
    metadata = storage.get_metadata("users")
    assert metadata.version == 1

    print(f"[PASS] Write append: {history.rows_added} rows")


def test_write_table_overwrite(storage):
    """Test writing data in overwrite mode."""
    schema = {"id": "int64"}
    storage.create_table("test", schema)

    # First write
    storage.write_table("test", {"id": [1, 2]}, mode="append")

    # Overwrite
    history = storage.write_table("test", {"id": [10, 20]}, mode="overwrite")

    assert history.mode == "overwrite"
    assert history.version == 2

    print("[PASS] Write overwrite")


def test_write_table_auto_create(storage):
    """Test auto-creating table on first write."""
    data = {"id": [1, 2], "value": [10, 20]}

    history = storage.write_table("auto_table", data, mode="append")

    assert history.operation == "WRITE"

    # Table should exist
    assert storage.table_exists("auto_table")
    metadata = storage.get_metadata("auto_table")
    assert "id" in metadata.schema

    print("[PASS] Auto table creation on write")


def test_read_table(storage):
    """Test reading table data."""
    schema = {"id": "int64", "name": "string"}
    storage.create_table("users", schema)

    # Write data
    data = {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]}
    storage.write_table("users", data, mode="append")

    # Read data
    result = storage.read_table("users")

    assert "id" in result
    assert "name" in result
    assert len(result["id"]) == 3

    print(f"[PASS] Read table: {len(result['id'])} rows")


def test_read_table_with_columns(storage):
    """Test reading specific columns."""
    schema = {"id": "int64", "name": "string", "age": "int32"}
    storage.create_table("users", schema)

    data = {"id": [1], "name": ["Alice"], "age": [25]}
    storage.write_table("users", data)

    # Read specific columns
    result = storage.read_table("users", columns=["id", "name"])

    assert len(result) == 2
    assert "id" in result
    assert "name" in result
    assert "age" not in result

    print(f"[PASS] Read with column selection: {list(result.keys())}")


def test_time_travel_by_version(storage):
    """Test time travel by version."""
    schema = {"id": "int64", "value": "int32"}
    storage.create_table("test", schema)

    # Version 1
    storage.write_table("test", {"id": [1], "value": [10]}, mode="overwrite")

    # Version 2
    storage.write_table("test", {"id": [2], "value": [20]}, mode="overwrite")

    # Read version 1
    result_v1 = storage.read_table("test", version=1)

    assert "id" in result_v1
    assert len(result_v1["id"]) >= 1

    print(f"[PASS] Time travel by version: v1 has {len(result_v1['id'])} rows")


def test_list_tables(storage):
    """Test listing tables."""
    storage.create_table("table1", {"id": "int64"})
    storage.create_table("table2", {"id": "int64"})
    storage.create_table("table3", {"id": "int64"})

    tables = storage.list_tables()

    assert len(tables) == 3
    assert "table1" in tables
    assert "table2" in tables
    assert "table3" in tables

    print(f"[PASS] List tables: {tables}")


def test_search_tables(storage):
    """Test searching tables with pattern."""
    storage.create_table("users_prod", {"id": "int64"})
    storage.create_table("users_dev", {"id": "int64"})
    storage.create_table("orders", {"id": "int64"})

    # Search for users_*
    results = storage.search_tables("users_*")

    assert len(results) == 2
    assert "users_prod" in results
    assert "users_dev" in results
    assert "orders" not in results

    print(f"[PASS] Search tables: {results}")


def test_table_exists(storage):
    """Test checking if table exists."""
    storage.create_table("test", {"id": "int64"})

    assert storage.table_exists("test") is True
    assert storage.table_exists("nonexistent") is False

    print("[PASS] Table exists check")


def test_get_metadata(storage):
    """Test getting table metadata."""
    schema = {"id": "int64", "name": "string"}
    storage.create_table("users", schema, description="User data")

    metadata = storage.get_metadata("users")

    assert metadata.name == "users"
    assert metadata.schema == schema
    assert metadata.description == "User data"

    print(f"[PASS] Get metadata: {metadata.name}")


def test_get_history(storage):
    """Test getting table history."""
    storage.create_table("test", {"id": "int64"})
    storage.write_table("test", {"id": [1]}, mode="append")
    storage.write_table("test", {"id": [2]}, mode="append")

    history = storage.get_history("test")

    assert len(history) >= 2
    assert any(h.operation == "CREATE" for h in history)
    assert any(h.operation == "WRITE" for h in history)

    print(f"[PASS] Get history: {len(history)} entries")


def test_get_statistics(storage):
    """Test getting table statistics."""
    storage.create_table("test", {"id": "int64"})
    storage.write_table("test", {"id": [1, 2, 3]}, mode="append")

    stats = storage.get_statistics("test")

    assert stats.table_name == "test"
    assert stats.total_files >= 1
    assert stats.total_size_bytes > 0

    print(f"[PASS] Statistics: {stats.total_files} files, {stats.total_size_bytes} bytes")


def test_merge_operation(storage):
    """Test MERGE/UPSERT operation."""
    schema = {"id": "int64", "status": "string"}
    storage.create_table("users", schema)

    # Initial data
    storage.write_table("users", {"id": [1, 2], "status": ["old", "old"]})

    # Merge data
    source = {"id": [1, 3], "status": ["new", "new"]}
    merge_op = MergeOperation(
        merge_condition="target.id = source.id",
        when_matched_update={"status": "source.status"},
        when_not_matched_insert={"id": "source.id", "status": "source.status"},
    )

    history = storage.merge("users", source, merge_op)

    assert history.operation == "MERGE"

    print(f"[PASS] MERGE operation: {history.rows_updated} updated")


def test_optimize_operation(storage):
    """Test OPTIMIZE operation."""
    storage.create_table("test", {"id": "int64"})
    storage.write_table("test", {"id": [1, 2, 3]})

    history = storage.optimize("test", z_order_by=["id"])

    assert history.operation == "OPTIMIZE"
    assert history.files_added > 0 or history.files_removed > 0

    print(f"[PASS] OPTIMIZE: +{history.files_added} -{history.files_removed} files")


def test_vacuum_operation(storage):
    """Test VACUUM operation."""
    storage.create_table("test", {"id": "int64"})
    storage.write_table("test", {"id": [1]})

    # Dry run
    history = storage.vacuum("test", retention_hours=168, dry_run=True)

    assert history.operation == "VACUUM"

    print(f"[PASS] VACUUM (dry run): {history.files_removed} files would be removed")


def test_vacuum_operation_execute(storage):
    """Test VACUUM operation execution."""
    storage.create_table("test", {"id": "int64"})
    storage.write_table("test", {"id": [1]})

    # Execute
    history = storage.vacuum("test", retention_hours=0, dry_run=False)

    assert history.operation == "VACUUM"

    print(f"[PASS] VACUUM (execute): {history.files_removed} files removed")


def test_multiple_writes_append(storage):
    """Test multiple append writes."""
    storage.create_table("test", {"id": "int64"})

    storage.write_table("test", {"id": [1, 2]}, mode="append")
    storage.write_table("test", {"id": [3, 4]}, mode="append")
    storage.write_table("test", {"id": [5, 6]}, mode="append")

    metadata = storage.get_metadata("test")
    assert metadata.version == 3

    result = storage.read_table("test")
    assert len(result["id"]) >= 6

    print(f"[PASS] Multiple appends: version={metadata.version}, rows={len(result['id'])}")


def test_partition_table_write(storage):
    """Test writing to partitioned table."""
    schema = {"id": "int64", "date": "string", "value": "double"}
    storage.create_table("metrics", schema, partition_by=["date"])

    data = {
        "id": [1, 2, 3],
        "date": ["2025-01-01", "2025-01-01", "2025-01-02"],
        "value": [10.0, 20.0, 30.0],
    }

    history = storage.write_table("metrics", data, mode="append")

    assert history.rows_added == 3

    print(f"[PASS] Partitioned write: {history.rows_added} rows")


def test_operations_enum():
    """Test operation enums."""
    assert WriteMode.APPEND.value == "append"
    assert WriteMode.OVERWRITE.value == "overwrite"

    print("[PASS] Operation enums")


def test_merge_operation_config():
    """Test merge operation configuration."""
    merge = MergeOperation(
        source_alias="src",
        target_alias="tgt",
        merge_condition="tgt.id = src.id",
    )

    assert merge.source_alias == "src"
    assert merge.target_alias == "tgt"

    print("[PASS] Merge operation config")


def test_optimize_operation_config():
    """Test optimize operation configuration."""
    optimize = OptimizeOperation(
        z_order_by=["col1", "col2"],
        max_file_size_mb=256,
    )

    assert optimize.z_order_by == ["col1", "col2"]
    assert optimize.max_file_size_mb == 256

    print("[PASS] Optimize operation config")


def test_vacuum_operation_config():
    """Test vacuum operation configuration."""
    vacuum = VacuumOperation(
        retention_hours=336,  # 14 days
        dry_run=True,
    )

    assert vacuum.retention_hours == 336
    assert vacuum.dry_run is True

    print("[PASS] Vacuum operation config")


# ===== Integration Tests =====

def test_full_workflow(storage):
    """Test complete workflow."""
    # Create table
    schema = {"id": "int64", "name": "string", "age": "int32"}
    metadata = storage.create_table("users", schema, description="User data")

    assert metadata.version == 0

    # Write data (v1)
    data1 = {"id": [1, 2], "name": ["Alice", "Bob"], "age": [25, 30]}
    storage.write_table("users", data1, mode="overwrite")

    # Write more data (v2)
    data2 = {"id": [3], "name": ["Charlie"], "age": [35]}
    storage.write_table("users", data2, mode="append")

    # Read latest
    result = storage.read_table("users")
    assert len(result["id"]) >= 3

    # Get history
    history = storage.get_history("users")
    assert len(history) >= 2

    # Get stats
    stats = storage.get_statistics("users")
    assert stats.total_files >= 1

    # Optimize
    storage.optimize("users")

    # List tables
    tables = storage.list_tables()
    assert "users" in tables

    print(f"[PASS] Full workflow: {len(result['id'])} rows, {len(history)} history entries")


def test_concurrent_tables(storage):
    """Test managing multiple tables."""
    # Create multiple tables
    storage.create_table("users", {"id": "int64", "name": "string"})
    storage.create_table("orders", {"id": "int64", "amount": "double"})
    storage.create_table("products", {"id": "int64", "price": "double"})

    # Write to each
    storage.write_table("users", {"id": [1], "name": ["Alice"]})
    storage.write_table("orders", {"id": [1], "amount": [99.99]})
    storage.write_table("products", {"id": [1], "price": [49.99]})

    # List all
    tables = storage.list_tables()
    assert len(tables) == 3

    # Read each
    users = storage.read_table("users")
    orders = storage.read_table("orders")
    products = storage.read_table("products")

    assert len(users["id"]) == 1
    assert len(orders["id"]) == 1
    assert len(products["id"]) == 1

    print(f"[PASS] Concurrent tables: {len(tables)} tables managed")


def run_manual_tests():
    """Run all tests manually."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    storage = NCFStorageManager(base_path=temp_dir)

    try:
        print("=== TableMetadata Tests ===\n")
        test_table_metadata_creation()
        test_table_metadata_serialization()
        test_table_metadata_save_load(temp_dir)

        print("\n=== TableHistory Tests ===\n")
        test_table_history_creation()
        test_table_history_serialization()

        print("\n=== DeltaStorageManager Tests ===\n")
        test_storage_manager_creation(temp_dir)
        test_create_table(storage)
        test_create_table_with_partitions(storage)
        test_create_table_already_exists(storage)
        test_create_table_overwrite(storage)

        print("\n=== Write Operations ===\n")
        test_write_table_append(storage)
        test_write_table_overwrite(storage)
        test_write_table_auto_create(storage)

        print("\n=== Read Operations ===\n")
        test_read_table(storage)
        test_read_table_with_columns(storage)
        test_time_travel_by_version(storage)

        print("\n=== Table Discovery ===\n")
        test_list_tables(storage)
        test_search_tables(storage)
        test_table_exists(storage)

        print("\n=== Metadata and History ===\n")
        test_get_metadata(storage)
        test_get_history(storage)
        test_get_statistics(storage)

        print("\n=== Advanced Operations ===\n")
        test_merge_operation(storage)
        test_optimize_operation(storage)
        test_vacuum_operation(storage)
        test_vacuum_operation_execute(storage)

        print("\n=== Additional Tests ===\n")
        test_multiple_writes_append(storage)
        test_partition_table_write(storage)
        test_operations_enum()
        test_merge_operation_config()
        test_optimize_operation_config()
        test_vacuum_operation_config()

        print("\n=== Integration Tests ===\n")
        test_full_workflow(storage)
        test_concurrent_tables(storage)

        print("\n[SUCCESS] All storage tests passed!")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    run_manual_tests()
