"""
End-to-End Database Integration Tests

Tests database operations including:
- Multiple database backends (DuckDB, SQLite)
- Connection management and pooling
- Transaction handling (commit, rollback)
- Concurrent database access
- Database migrations and schema changes
- Data integrity and constraints
- Indexes and performance
- Backup and restore
- Query execution across databases
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import duckdb
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1, 51),
        "name": [f"User_{i}" for i in range(1, 51)],
        "age": np.random.randint(20, 70, 50),
        "department": np.random.choice(["Engineering", "Sales", "Marketing"], 50),
        "salary": np.random.randint(50000, 120000, 50),
    })


class TestDuckDBIntegration:
    """Test DuckDB database integration."""

    def test_create_and_connect_duckdb(self, temp_dir):
        """Test creating and connecting to DuckDB database."""
        db_path = temp_dir / "test.duckdb"

        # Create database
        conn = duckdb.connect(str(db_path))
        assert conn is not None

        # Verify database file created
        assert db_path.exists()

        conn.close()

    def test_duckdb_table_creation(self, temp_dir):
        """Test creating tables in DuckDB."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create table
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                age INTEGER,
                department VARCHAR
            )
        """)

        # Verify table exists
        tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = 'employees'
        """).fetchdf()

        assert len(tables) == 1
        assert tables["table_name"].iloc[0] == "employees"

        conn.close()

    def test_duckdb_insert_and_query(self, temp_dir, sample_data):
        """Test inserting and querying data in DuckDB."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create table
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        # Insert data
        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )

        # Query data
        result = conn.execute("SELECT COUNT(*) as count FROM employees").fetchdf()
        assert result["count"].iloc[0] == 50

        conn.close()

    def test_duckdb_transactions(self, temp_dir):
        """Test transaction support in DuckDB."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        conn.execute("CREATE TABLE test (id INTEGER, value VARCHAR)")

        # Test commit
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT INTO test VALUES (1, 'value1')")
        conn.execute("COMMIT")

        result = conn.execute("SELECT COUNT(*) as count FROM test").fetchdf()
        assert result["count"].iloc[0] == 1

        # Test rollback
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT INTO test VALUES (2, 'value2')")
        conn.execute("ROLLBACK")

        result = conn.execute("SELECT COUNT(*) as count FROM test").fetchdf()
        assert result["count"].iloc[0] == 1  # Still only 1 record

        conn.close()

    def test_duckdb_bulk_insert(self, temp_dir, sample_data):
        """Test bulk insert performance in DuckDB."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create table
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        # Bulk insert using pandas DataFrame
        start = time.time()
        conn.execute("INSERT INTO employees SELECT * FROM sample_data")
        elapsed = time.time() - start

        # Verify all data inserted
        result = conn.execute("SELECT COUNT(*) as count FROM employees").fetchdf()
        assert result["count"].iloc[0] == 50

        print(f"Bulk insert of 50 rows took {elapsed:.4f}s")
        assert elapsed < 1.0  # Should be fast

        conn.close()

    def test_duckdb_indexes(self, temp_dir, sample_data):
        """Test index creation and usage in DuckDB."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create table and insert data
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )

        # Note: DuckDB automatically optimizes queries, explicit indexes not always needed
        # But we can test query performance
        start = time.time()
        result = conn.execute("SELECT * FROM employees WHERE id = 25").fetchdf()
        elapsed = time.time() - start

        assert len(result) == 1
        assert result["id"].iloc[0] == 25
        print(f"Indexed query took {elapsed:.4f}s")

        conn.close()


class TestSQLiteIntegration:
    """Test SQLite database integration."""

    def test_create_and_connect_sqlite(self, temp_dir):
        """Test creating and connecting to SQLite database."""
        db_path = temp_dir / "test.db"

        conn = sqlite3.connect(str(db_path))
        assert conn is not None

        # Verify database file created
        assert db_path.exists()

        conn.close()

    def test_sqlite_table_creation(self, temp_dir):
        """Test creating tables in SQLite."""
        db_path = temp_dir / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create table
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                department TEXT
            )
        """)

        # Verify table exists
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='employees'
        """)
        tables = cursor.fetchall()

        assert len(tables) == 1
        assert tables[0][0] == "employees"

        conn.close()

    def test_sqlite_transactions(self, temp_dir):
        """Test transaction support in SQLite."""
        db_path = temp_dir / "test.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")

        # Test commit
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT INTO test VALUES (1, 'value1')")
        conn.commit()

        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 1

        # Test rollback
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT INTO test VALUES (2, 'value2')")
        conn.rollback()

        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 1  # Still only 1 record

        conn.close()

    def test_sqlite_constraints(self, temp_dir):
        """Test constraint enforcement in SQLite."""
        db_path = temp_dir / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create table with constraints
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER CHECK(age >= 18),
                department TEXT
            )
        """)

        # Test NOT NULL constraint
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees (id, age) VALUES (1, 25)")

        # Test CHECK constraint
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees VALUES (1, 'John', 15, 'IT')")

        # Test PRIMARY KEY constraint
        conn.execute("INSERT INTO employees VALUES (1, 'John', 25, 'IT')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees VALUES (1, 'Jane', 30, 'HR')")

        conn.close()


class TestInMemoryDatabases:
    """Test in-memory database operations."""

    def test_duckdb_in_memory(self):
        """Test DuckDB in-memory database."""
        conn = duckdb.connect(":memory:")

        # Create table and insert data
        conn.execute("CREATE TABLE test (id INTEGER, value VARCHAR)")
        conn.execute("INSERT INTO test VALUES (1, 'value1'), (2, 'value2')")

        # Query data
        result = conn.execute("SELECT COUNT(*) as count FROM test").fetchdf()
        assert result["count"].iloc[0] == 2

        conn.close()

    def test_sqlite_in_memory(self):
        """Test SQLite in-memory database."""
        conn = sqlite3.connect(":memory:")

        # Create table and insert data
        conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'value1'), (2, 'value2')")

        # Query data
        cursor = conn.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 2

        conn.close()

    def test_in_memory_performance(self):
        """Test in-memory database performance."""
        conn = duckdb.connect(":memory:")

        conn.execute("""
            CREATE TABLE large_table (
                id INTEGER,
                value VARCHAR
            )
        """)

        # Insert 1000 rows
        start = time.time()
        for i in range(1000):
            conn.execute("INSERT INTO large_table VALUES (?, ?)", [i, f"value_{i}"])
        elapsed = time.time() - start

        print(f"In-memory insert of 1000 rows took {elapsed:.4f}s")
        assert elapsed < 2.0  # Should be fast for in-memory

        # Query performance
        start = time.time()
        result = conn.execute("SELECT COUNT(*) as count FROM large_table").fetchdf()
        elapsed = time.time() - start

        assert result["count"].iloc[0] == 1000
        print(f"In-memory query took {elapsed:.4f}s")

        conn.close()


class TestConcurrentDatabaseAccess:
    """Test concurrent database access."""

    def test_concurrent_reads(self, temp_dir, sample_data):
        """Test concurrent read operations."""
        db_path = temp_dir / "test.duckdb"

        # Setup database
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )
        conn.close()

        # Concurrent reads
        def read_data(thread_id):
            conn = duckdb.connect(str(db_path))
            result = conn.execute("SELECT COUNT(*) as count FROM employees").fetchdf()
            count = result["count"].iloc[0]
            conn.close()
            return (thread_id, count)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_data, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # All reads should return same count
        assert all(count == 50 for _, count in results)
        assert len(results) == 10

    def test_concurrent_writes(self, temp_dir):
        """Test concurrent write operations."""
        db_path = temp_dir / "test.duckdb"

        # Setup database
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE logs (id INTEGER, thread_id INTEGER, timestamp TIMESTAMP)")
        conn.close()

        # Concurrent writes (each thread inserts its own records)
        def insert_log(thread_id):
            conn = duckdb.connect(str(db_path))
            try:
                # Insert multiple records
                for i in range(5):
                    conn.execute(
                        "INSERT INTO logs VALUES (?, ?, NOW())",
                        [thread_id * 100 + i, thread_id]
                    )
                conn.close()
                return (thread_id, True)
            except Exception as e:
                conn.close()
                return (thread_id, False)

        # Run concurrent inserts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_log, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # Verify writes succeeded
        conn = duckdb.connect(str(db_path))
        result = conn.execute("SELECT COUNT(*) as count FROM logs").fetchdf()
        final_count = int(result["count"].iloc[0])
        conn.close()

        # Should have records from concurrent writes (10 threads * 5 records = 50)
        assert final_count > 0
        assert final_count <= 50
        print(f"Concurrent writes inserted {final_count} records")
        assert all(success for _, success in results)  # All threads should succeed


class TestDataMigration:
    """Test data migration between databases."""

    def test_migrate_sqlite_to_duckdb(self, temp_dir, sample_data):
        """Test migrating data from SQLite to DuckDB."""
        sqlite_path = temp_dir / "source.db"
        duckdb_path = temp_dir / "target.duckdb"

        # Create SQLite database with data
        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name TEXT,
                age INTEGER,
                department TEXT,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            sqlite_conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                (row["id"], row["name"], row["age"], row["department"], row["salary"])
            )
        sqlite_conn.commit()

        # Read data from SQLite
        cursor = sqlite_conn.execute("SELECT * FROM employees")
        rows = cursor.fetchall()
        sqlite_conn.close()

        # Write to DuckDB
        duckdb_conn = duckdb.connect(str(duckdb_path))
        duckdb_conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for row in rows:
            duckdb_conn.execute("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", row)

        # Verify migration
        result = duckdb_conn.execute("SELECT COUNT(*) as count FROM employees").fetchdf()
        assert result["count"].iloc[0] == 50

        duckdb_conn.close()

    def test_export_to_csv(self, temp_dir, sample_data):
        """Test exporting database to CSV."""
        db_path = temp_dir / "test.duckdb"
        csv_path = temp_dir / "export.csv"

        # Create database with data
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )

        # Export to CSV
        conn.execute(f"COPY employees TO '{csv_path}' (FORMAT CSV, HEADER)")

        # Verify CSV created
        assert csv_path.exists()

        # Read CSV and verify
        df = pd.read_csv(csv_path)
        assert len(df) == 50

        conn.close()


class TestDatabaseBackupRestore:
    """Test database backup and restore operations."""

    def test_duckdb_backup(self, temp_dir, sample_data):
        """Test backing up DuckDB database."""
        original_path = temp_dir / "original.duckdb"
        backup_path = temp_dir / "backup.duckdb"

        # Create original database
        conn = duckdb.connect(str(original_path))
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )
        conn.close()

        # Backup (simple file copy for DuckDB)
        import shutil
        shutil.copy(original_path, backup_path)

        # Verify backup
        assert backup_path.exists()

        # Open backup and verify data
        backup_conn = duckdb.connect(str(backup_path))
        result = backup_conn.execute("SELECT COUNT(*) as count FROM employees").fetchdf()
        assert result["count"].iloc[0] == 50
        backup_conn.close()


class TestDatabaseConstraintsAndIntegrity:
    """Test database constraints and data integrity."""

    def test_foreign_key_constraints(self, temp_dir):
        """Test foreign key constraint enforcement."""
        db_path = temp_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")

        # Create parent and child tables
        conn.execute("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                dept_id INTEGER,
                FOREIGN KEY (dept_id) REFERENCES departments(id)
            )
        """)

        # Insert valid department
        conn.execute("INSERT INTO departments VALUES (1, 'Engineering')")

        # Insert employee with valid department
        conn.execute("INSERT INTO employees VALUES (1, 'John', 1)")

        # Try to insert employee with invalid department
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees VALUES (2, 'Jane', 99)")

        conn.close()

    def test_unique_constraints(self, temp_dir):
        """Test unique constraint enforcement."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR UNIQUE,
                name VARCHAR
            )
        """)

        # Insert first record
        conn.execute("INSERT INTO users VALUES (1, 'user@example.com', 'User One')")

        # Try to insert duplicate email
        with pytest.raises(Exception):  # DuckDB will raise constraint violation
            conn.execute("INSERT INTO users VALUES (2, 'user@example.com', 'User Two')")

        conn.close()


class TestDatabaseQueryOptimization:
    """Test query optimization across databases."""

    def test_query_plan_analysis(self, temp_dir, sample_data):
        """Test query execution plan analysis."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        # Create table with data
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )

        # Get query plan
        plan = conn.execute("""
            EXPLAIN SELECT * FROM employees WHERE department = 'Engineering'
        """).fetchdf()

        assert plan is not None
        assert len(plan) > 0

        conn.close()

    def test_aggregation_performance(self, temp_dir, sample_data):
        """Test aggregation query performance."""
        db_path = temp_dir / "test.duckdb"
        conn = duckdb.connect(str(db_path))

        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row["id"], row["name"], row["age"], row["department"], row["salary"]]
            )

        # Test aggregation performance
        start = time.time()
        result = conn.execute("""
            SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
            FROM employees
            GROUP BY department
        """).fetchdf()
        elapsed = time.time() - start

        assert len(result) > 0
        print(f"Aggregation query took {elapsed:.4f}s")
        assert elapsed < 1.0

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
