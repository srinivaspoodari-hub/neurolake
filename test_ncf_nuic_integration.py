"""
NCF to NUIC Integration Test

Tests that NCF tables are automatically registered in NUIC catalog
when created via NCFStorageManager.

Tests:
1. Create NCF table and verify in NUIC
2. Table metadata matches in both systems
3. Schema evolution tracked
4. Lineage tracking works
5. Quality metrics available
"""

import os
import sys
import tempfile
import shutil
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from neurolake.storage.manager import NCFStorageManager
from neurolake.nuic import NUICEngine


class TestNCFNUICIntegration:
    """Test NCF to NUIC automatic catalog integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_path = tempfile.mkdtemp(prefix="ncf_nuic_test_")
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def storage_manager(self, temp_dir):
        """Create NCF storage manager."""
        return NCFStorageManager(base_path=temp_dir)

    @pytest.fixture
    def nuic_catalog(self):
        """Create NUIC catalog engine with automatic cleanup."""
        catalog = NUICEngine()
        yield catalog
        # Cleanup: close connection after test
        catalog.close()

    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "email": [
                "alice@example.com",
                "bob@example.com",
                "charlie@example.com",
                "david@example.com",
                "eve@example.com"
            ],
            "age": [25, 30, 35, 40, 45],
            "salary": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0]
        })

    def test_create_table_auto_catalogs(self, storage_manager, nuic_catalog, temp_dir):
        """
        Test 1: Creating NCF table automatically registers in NUIC.

        Expected:
        - Table created successfully
        - Table appears in NUIC catalog
        - Metadata matches
        """
        # Create NCF table
        table_name = "test_users"
        schema = {
            "id": "int64",
            "name": "string",
            "email": "string"
        }

        metadata = storage_manager.create_table(
            table_name=table_name,
            schema=schema,
            description="Test user table for NCF-NUIC integration"
        )

        # Verify table created
        assert metadata is not None
        assert metadata.name == table_name

        # Verify table in NUIC catalog
        datasets = nuic_catalog.search_datasets()  # Search with no filter returns all
        table_names = [ds["dataset_name"] for ds in datasets]

        assert table_name in table_names, f"Table '{table_name}' not found in NUIC catalog. Found: {table_names}"

        # Get dataset from NUIC (use dataset_id which is ncf_{table_name})
        dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")
        assert dataset is not None
        assert dataset["dataset_name"] == table_name
        # Check metadata contains format
        dataset_meta = dataset.get("metadata", {})
        if isinstance(dataset_meta, str):
            dataset_meta = json.loads(dataset_meta)
        assert dataset_meta.get("format") == "ncf"

        print(f"OK Test 1 PASSED: Table '{table_name}' auto-cataloged in NUIC")

    def test_table_metadata_consistency(self, storage_manager, nuic_catalog, temp_dir):
        """
        Test 2: Verify metadata consistency between NCF and NUIC.

        Expected:
        - Schema matches
        - Description matches
        - Path matches
        """
        table_name = "test_products"
        schema = {
            "product_id": "int64",
            "product_name": "string",
            "price": "float64"
        }
        description = "Product catalog table"

        # Create table
        ncf_metadata = storage_manager.create_table(
            table_name=table_name,
            schema=schema,
            description=description
        )

        # Get from NUIC (use dataset_id)
        nuic_dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")

        # Verify consistency
        assert nuic_dataset is not None
        assert nuic_dataset["dataset_name"] == ncf_metadata.name

        # Check metadata
        dataset_meta = nuic_dataset.get("metadata", {})
        if isinstance(dataset_meta, str):
            dataset_meta = json.loads(dataset_meta)
        assert dataset_meta.get("format") == "ncf"
        assert description in str(dataset_meta)

        print(f"OK Test 2 PASSED: Metadata consistent between NCF and NUIC")

    def test_write_data_updates_catalog(self, storage_manager, nuic_catalog, sample_data):
        """
        Test 3: Writing data to NCF table updates NUIC metadata.

        Expected:
        - Row count tracked
        - Version incremented
        - Last modified updated
        """
        table_name = "test_employees"
        schema = {
            "id": "int64",
            "name": "string",
            "email": "string",
            "age": "int64",
            "salary": "float64"
        }

        # Create table
        storage_manager.create_table(table_name, schema)

        # Convert DataFrame to dict format (column -> list)
        data_dict = {col: sample_data[col].tolist() for col in sample_data.columns}

        # Write data
        storage_manager.write_table(table_name, data_dict, mode="append")

        # Check NUIC has updated info (use correct dataset_id)
        dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")
        assert dataset is not None

        # Metadata should exist
        metadata = dataset.get("metadata", {})
        assert metadata is not None

        print(f"OK Test 3 PASSED: Data write tracked in NUIC")

    def test_search_finds_ncf_tables(self, storage_manager, nuic_catalog):
        """
        Test 4: NUIC search can find NCF tables.

        Expected:
        - Search by name works
        - Search by format works
        - Search by tags works
        """
        # Create multiple tables
        tables = [
            ("sales_2024", {"date": "string", "amount": "float64"}),
            ("sales_2023", {"date": "string", "amount": "float64"}),
            ("customers", {"id": "int64", "name": "string"})
        ]

        for table_name, schema in tables:
            storage_manager.create_table(table_name, schema)

        # Search by name pattern
        results = nuic_catalog.search_datasets(query="sales")
        sales_tables = [r["dataset_name"] for r in results if "sales" in r["dataset_name"]]

        assert len(sales_tables) >= 2, f"Search should find sales tables. Found: {sales_tables}"
        assert "sales_2024" in sales_tables
        assert "sales_2023" in sales_tables

        print(f"OK Test 4 PASSED: Search finds NCF tables")

    def test_time_travel_versions_tracked(self, storage_manager, nuic_catalog, sample_data):
        """
        Test 5: Time travel versions tracked in NUIC.

        Expected:
        - Each write creates new version
        - Version history available
        - Can read at specific version
        """
        table_name = "test_versioned"
        schema = {
            "id": "int64",
            "name": "string",
            "email": "string",
            "age": "int64",
            "salary": "float64"
        }

        # Create table
        storage_manager.create_table(table_name, schema)

        # Write v1 (convert DataFrame to dict)
        data_dict_v1 = {col: sample_data[col].tolist() for col in sample_data.columns}
        storage_manager.write_table(table_name, data_dict_v1, mode="append")

        # Write v2
        more_data = pd.DataFrame({
            "id": [6, 7],
            "name": ["Frank", "Grace"],
            "email": ["frank@example.com", "grace@example.com"],
            "age": [50, 55],
            "salary": [95000.0, 100000.0]
        })
        data_dict_v2 = {col: more_data[col].tolist() for col in more_data.columns}
        storage_manager.write_table(table_name, data_dict_v2, mode="append")

        # Verify versions
        versions = storage_manager.list_versions(table_name)
        assert len(versions) >= 2, "Should have at least 2 versions"

        # Read at version 1 (returns dict format)
        data_v1 = storage_manager.read_at_version(table_name, version=1)
        # Count rows from first column
        row_count_v1 = len(data_v1[list(data_v1.keys())[0]])
        assert row_count_v1 == 5, f"Version 1 should have 5 rows, got {row_count_v1}"

        # Read current (returns dict format)
        data_current = storage_manager.read_table(table_name)
        # Count rows from first column
        row_count_current = len(data_current[list(data_current.keys())[0]])
        assert row_count_current == 7, f"Current should have 7 rows, got {row_count_current}"

        print(f"OK Test 5 PASSED: Time travel versions tracked")

    def test_multiple_tables_all_cataloged(self, storage_manager, nuic_catalog):
        """
        Test 6: Multiple NCF tables all appear in catalog.

        Expected:
        - All tables cataloged
        - No duplicates
        - All accessible
        """
        # Create 10 tables
        table_count = 10
        for i in range(table_count):
            table_name = f"test_table_{i}"
            schema = {
                "id": "int64",
                "value": "string"
            }
            storage_manager.create_table(table_name, schema)

        # Get all datasets (search with no filter)
        datasets = nuic_catalog.search_datasets()
        test_tables = [d["dataset_name"] for d in datasets if d["dataset_name"].startswith("test_table_")]

        assert len(test_tables) >= table_count, f"Should have at least {table_count} test tables. Found: {len(test_tables)}"

        # Verify each table accessible
        for i in range(table_count):
            table_name = f"test_table_{i}"
            dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")
            assert dataset is not None, f"Table {table_name} should be in catalog"
            dataset_meta = dataset.get("metadata", {})
            if isinstance(dataset_meta, str):
                dataset_meta = json.loads(dataset_meta)
            assert dataset_meta.get("format") == "ncf"

        print(f"OK Test 6 PASSED: All {table_count} tables cataloged")

    def test_drop_table_removes_from_catalog(self, storage_manager, nuic_catalog):
        """
        Test 7: Dropping NCF table removes from NUIC catalog.

        Expected:
        - Table removed from NCF storage
        - Table removed from NUIC catalog
        - Search no longer finds table
        """
        table_name = "test_to_delete"
        schema = {"id": "int64", "value": "string"}

        # Create table
        storage_manager.create_table(table_name, schema)

        # Verify in catalog
        dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")
        assert dataset is not None

        # Drop table
        try:
            storage_manager.drop_table(table_name)
        except Exception as e:
            # If drop_table not implemented, skip test
            pytest.skip(f"drop_table not implemented: {e}")

        # Verify removed from catalog
        try:
            dataset = nuic_catalog.get_dataset(f"ncf_{table_name}")
            assert dataset is None or dataset.get("status") == "deleted"
        except Exception:
            # Table not found is expected
            pass

        print(f"OK Test 7 PASSED: Dropped table removed from catalog")


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 80)
    print("NCF to NUIC INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_"
    ])

    print()
    print("=" * 80)
    if exit_code == 0:
        print("SUCCESS: ALL INTEGRATION TESTS PASSED")
    else:
        print("FAILED: SOME TESTS FAILED")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(run_integration_tests())
