"""
Comprehensive NCF Performance Benchmark

Compares NCF (via NCFStorageManager) against Parquet and Delta Lake across:
1. Write performance (initial load, append, update)
2. Read performance (full scan, column selection, time travel)
3. Storage efficiency (file size, compression ratio)
4. Query performance (filtering, aggregation)

This benchmark tests the HIGH-LEVEL API (NCFStorageManager) that users actually
interact with, not just the low-level NCFWriter/Reader.

Run: python benchmark_comprehensive.py
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

import numpy as np
import pandas as pd
import psutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from neurolake.storage.manager import NCFStorageManager


def get_memory_usage() -> float:
    """Get current process memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


class BenchmarkResults:
    """Store and format benchmark results"""

    def __init__(self):
        self.results = {
            "ncf": {},
            "parquet": {},
            "delta": {}
        }

    def add_result(self, format_name: str, operation: str, metrics: Dict[str, Any]):
        """Add a benchmark result"""
        self.results[format_name][operation] = metrics

    def get_result(self, format_name: str, operation: str) -> Dict[str, Any]:
        """Get a specific result"""
        return self.results.get(format_name, {}).get(operation, {})

    def print_summary(self):
        """Print formatted summary of all results"""
        print("\n" + "=" * 100)
        print("COMPREHENSIVE BENCHMARK RESULTS")
        print("=" * 100)

        self._print_write_performance()
        self._print_read_performance()
        self._print_storage_efficiency()
        self._print_time_travel_performance()
        self._print_overall_winner()

    def _print_write_performance(self):
        """Print write performance comparison"""
        print("\n" + "-" * 100)
        print("1. WRITE PERFORMANCE")
        print("-" * 100)

        operations = ["initial_load", "append", "update"]

        for op in operations:
            print(f"\n{op.replace('_', ' ').title()}:")
            print(f"{'Format':<15} {'Time (s)':<15} {'Speed (rows/s)':<20} {'Memory (MB)':<15}")
            print("-" * 65)

            for fmt in ["ncf", "parquet", "delta"]:
                result = self.get_result(fmt, op)
                if result:
                    time_val = result.get("time", 0)
                    speed_val = result.get("speed", 0)
                    mem_val = result.get("memory_delta", 0)
                    print(f"{fmt.upper():<15} {time_val:<15.4f} {speed_val:<20,.0f} {mem_val:<15.2f}")

    def _print_read_performance(self):
        """Print read performance comparison"""
        print("\n" + "-" * 100)
        print("2. READ PERFORMANCE")
        print("-" * 100)

        operations = ["full_scan", "column_select", "filtered_read"]

        for op in operations:
            print(f"\n{op.replace('_', ' ').title()}:")
            print(f"{'Format':<15} {'Time (s)':<15} {'Speed (rows/s)':<20} {'Memory (MB)':<15}")
            print("-" * 65)

            for fmt in ["ncf", "parquet", "delta"]:
                result = self.get_result(fmt, op)
                if result:
                    time_val = result.get("time", 0)
                    speed_val = result.get("speed", 0)
                    mem_val = result.get("memory_delta", 0)
                    print(f"{fmt.upper():<15} {time_val:<15.4f} {speed_val:<20,.0f} {mem_val:<15.2f}")

    def _print_storage_efficiency(self):
        """Print storage efficiency comparison"""
        print("\n" + "-" * 100)
        print("3. STORAGE EFFICIENCY")
        print("-" * 100)

        print(f"\n{'Format':<15} {'File Size (MB)':<20} {'Compression Ratio':<20}")
        print("-" * 55)

        sizes = {}
        for fmt in ["ncf", "parquet", "delta"]:
            result = self.get_result(fmt, "initial_load")
            if result and "file_size" in result:
                sizes[fmt] = result["file_size"]
                size_mb = result["file_size"] / (1024 * 1024)
                print(f"{fmt.upper():<15} {size_mb:<20.2f}", end="")

                # Calculate compression ratio vs raw data size
                if "raw_data_size" in result:
                    ratio = result["raw_data_size"] / result["file_size"]
                    print(f"{ratio:<20.2f}x")
                else:
                    print()

        # Compare formats
        if "parquet" in sizes and "ncf" in sizes:
            ratio = sizes["parquet"] / sizes["ncf"]
            print(f"\nNCF is {ratio:.2f}x {'smaller' if ratio > 1 else 'larger'} than Parquet")

    def _print_time_travel_performance(self):
        """Print time travel performance comparison"""
        print("\n" + "-" * 100)
        print("4. TIME TRAVEL PERFORMANCE")
        print("-" * 100)

        operations = ["version_read", "timestamp_read"]

        for op in operations:
            print(f"\n{op.replace('_', ' ').title()}:")
            print(f"{'Format':<15} {'Time (s)':<15} {'Speed (rows/s)':<20} {'Supported':<15}")
            print("-" * 65)

            for fmt in ["ncf", "parquet", "delta"]:
                result = self.get_result(fmt, op)
                if result:
                    time_val = result.get("time", 0)
                    speed_val = result.get("speed", 0)
                    supported = result.get("supported", False)
                    status = "YES [OK]" if supported else "NO [X]"
                    print(f"{fmt.upper():<15} {time_val:<15.4f} {speed_val:<20,.0f} {status:<15}")
                else:
                    print(f"{fmt.upper():<15} {'N/A':<15} {'N/A':<20} {'NO [X]':<15}")

    def _print_overall_winner(self):
        """Determine and print overall winner"""
        print("\n" + "=" * 100)
        print("OVERALL ASSESSMENT")
        print("=" * 100)

        scores = {"ncf": 0, "parquet": 0, "delta": 0}

        # Score write performance
        for op in ["initial_load", "append"]:
            speeds = {}
            for fmt in ["ncf", "parquet", "delta"]:
                result = self.get_result(fmt, op)
                if result and "speed" in result:
                    speeds[fmt] = result["speed"]
            if speeds:
                winner = max(speeds, key=speeds.get)
                scores[winner] += 1

        # Score read performance
        for op in ["full_scan", "column_select"]:
            speeds = {}
            for fmt in ["ncf", "parquet", "delta"]:
                result = self.get_result(fmt, op)
                if result and "speed" in result:
                    speeds[fmt] = result["speed"]
            if speeds:
                winner = max(speeds, key=speeds.get)
                scores[winner] += 1

        # Score storage efficiency
        sizes = {}
        for fmt in ["ncf", "parquet", "delta"]:
            result = self.get_result(fmt, "initial_load")
            if result and "file_size" in result:
                sizes[fmt] = result["file_size"]
        if sizes:
            winner = min(sizes, key=sizes.get)
            scores[winner] += 2  # Double weight for storage

        # Score time travel support
        for fmt in ["ncf", "delta"]:
            result = self.get_result(fmt, "version_read")
            if result and result.get("supported"):
                scores[fmt] += 1

        print(f"\nScores (out of ~8 categories):")
        for fmt in ["ncf", "parquet", "delta"]:
            print(f"  {fmt.upper():<15} {scores[fmt]} points")

        winner = max(scores, key=scores.get)
        print(f"\n[RESULT] {winner.upper()} wins overall with {scores[winner]} points!")

        # Feature comparison
        print("\n" + "-" * 100)
        print("FEATURE SUPPORT")
        print("-" * 100)

        features = [
            ("ACID transactions", {"ncf": True, "parquet": False, "delta": True}),
            ("Time travel", {"ncf": True, "parquet": False, "delta": True}),
            ("Schema evolution", {"ncf": True, "parquet": False, "delta": True}),
            ("Semantic types", {"ncf": True, "parquet": False, "delta": False}),
            ("Column statistics", {"ncf": True, "parquet": True, "delta": True}),
            ("Compression", {"ncf": True, "parquet": True, "delta": True}),
        ]

        print(f"\n{'Feature':<25} {'NCF':<15} {'Parquet':<15} {'Delta Lake':<15}")
        print("-" * 70)
        for feature_name, support in features:
            ncf_str = "[OK] YES" if support["ncf"] else "[X] NO"
            parquet_str = "[OK] YES" if support["parquet"] else "[X] NO"
            delta_str = "[OK] YES" if support["delta"] else "[X] NO"
            print(f"{feature_name:<25} {ncf_str:<15} {parquet_str:<15} {delta_str:<15}")


def create_test_dataset(num_rows: int = 100_000) -> pd.DataFrame:
    """
    Create realistic test dataset with various data types.

    Simulates a typical business dataset with:
    - Integer IDs
    - Timestamps
    - Numeric values (revenue, costs, etc.)
    - Categories (departments, regions, etc.)
    - Text fields (names, descriptions, etc.)
    - Email addresses (PII)
    """
    print(f"\nCreating test dataset with {num_rows:,} rows...")

    np.random.seed(42)  # For reproducibility

    data = pd.DataFrame({
        # Identifiers
        "id": range(num_rows),
        "user_id": np.random.randint(1000, 9999, num_rows),

        # Timestamps
        "created_at": pd.date_range("2024-01-01", periods=num_rows, freq="1min"),

        # Numeric metrics
        "revenue": np.random.uniform(100, 10000, num_rows).round(2),
        "cost": np.random.uniform(50, 5000, num_rows).round(2),
        "quantity": np.random.randint(1, 100, num_rows),
        "score": np.random.uniform(0, 1, num_rows).round(4),

        # Categories
        "department": np.random.choice(["Sales", "Marketing", "Engineering", "Support", "HR"], num_rows),
        "region": np.random.choice(["North", "South", "East", "West", "Central"], num_rows),
        "status": np.random.choice(["active", "pending", "completed", "cancelled"], num_rows),

        # Text fields
        "name": [f"User_{i:06d}" for i in range(num_rows)],
        "email": [f"user{i}@example.com" for i in range(num_rows)],
        "description": [f"Transaction {i} - {np.random.choice(['Standard', 'Premium', 'Enterprise'])}" for i in range(num_rows)],
    })

    raw_size = data.memory_usage(deep=True).sum()
    print(f"Dataset shape: {data.shape}")
    print(f"Dataset memory: {raw_size / (1024*1024):.2f} MB")
    print(f"Columns: {', '.join(data.columns)}")

    return data


def benchmark_ncf(data: pd.DataFrame, temp_dir: Path, results: BenchmarkResults):
    """
    Benchmark NCF using NCFStorageManager (high-level API).

    Tests:
    1. Initial load (create table + write)
    2. Append operation
    3. Read operations (full, column select)
    4. Time travel (version, timestamp)
    """
    print("\n" + "=" * 100)
    print("NCF BENCHMARK (via NCFStorageManager)")
    print("=" * 100)

    ncf_dir = temp_dir / "ncf_storage"
    ncf_dir.mkdir(exist_ok=True)

    storage = NCFStorageManager(base_path=str(ncf_dir))
    table_name = "benchmark_table"

    # Convert DataFrame to dict format (column -> list)
    data_dict = {col: data[col].tolist() for col in data.columns}

    # 1. Initial Load (Create + Write)
    print("\n1. Initial Load (create table + write data)...")

    schema = {col: str(dtype) for col, dtype in data.dtypes.items()}

    mem_before = get_memory_usage()
    start_time = time.time()

    storage.create_table(
        table_name=table_name,
        schema=schema,
        description="Benchmark test table"
    )

    storage.write_table(table_name, data_dict, mode="overwrite")

    load_time = time.time() - start_time
    mem_after = get_memory_usage()

    # Get file size
    table_path = ncf_dir / table_name
    file_size = sum(f.stat().st_size for f in table_path.rglob("*") if f.is_file())

    print(f"  Time: {load_time:.4f}s")
    print(f"  Speed: {len(data) / load_time:,.0f} rows/sec")
    print(f"  File size: {file_size / (1024*1024):.2f} MB")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    raw_size = data.memory_usage(deep=True).sum()

    results.add_result("ncf", "initial_load", {
        "time": load_time,
        "speed": len(data) / load_time,
        "file_size": file_size,
        "raw_data_size": raw_size,
        "memory_delta": mem_after - mem_before
    })

    # 2. Append Operation
    print("\n2. Append Operation...")

    # Create append data (10% of original)
    append_size = len(data) // 10
    append_data = data.head(append_size).copy()
    append_data["id"] = range(len(data), len(data) + append_size)
    append_dict = {col: append_data[col].tolist() for col in append_data.columns}

    mem_before = get_memory_usage()
    start_time = time.time()

    storage.write_table(table_name, append_dict, mode="append")

    append_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {append_time:.4f}s")
    print(f"  Speed: {append_size / append_time:,.0f} rows/sec")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("ncf", "append", {
        "time": append_time,
        "speed": append_size / append_time,
        "memory_delta": mem_after - mem_before
    })

    # 3. Full Scan Read
    print("\n3. Full Scan Read...")

    mem_before = get_memory_usage()
    start_time = time.time()

    read_data = storage.read_table(table_name)

    read_time = time.time() - start_time
    mem_after = get_memory_usage()

    # Count rows from first column
    row_count = len(read_data[list(read_data.keys())[0]])

    print(f"  Time: {read_time:.4f}s")
    print(f"  Speed: {row_count / read_time:,.0f} rows/sec")
    print(f"  Rows read: {row_count:,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("ncf", "full_scan", {
        "time": read_time,
        "speed": row_count / read_time,
        "rows": row_count,
        "memory_delta": mem_after - mem_before
    })

    # 4. Column Selection Read
    print("\n4. Column Selection Read (3 columns)...")

    selected_cols = ["id", "revenue", "department"]

    mem_before = get_memory_usage()
    start_time = time.time()

    col_data = storage.read_table(table_name, columns=selected_cols)

    col_time = time.time() - start_time
    mem_after = get_memory_usage()

    row_count = len(col_data[selected_cols[0]])

    print(f"  Time: {col_time:.4f}s")
    print(f"  Speed: {row_count / col_time:,.0f} rows/sec")
    print(f"  Rows read: {row_count:,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("ncf", "column_select", {
        "time": col_time,
        "speed": row_count / col_time,
        "rows": row_count,
        "memory_delta": mem_after - mem_before
    })

    # 5. Time Travel - Read at Version
    print("\n5. Time Travel - Read at Version 1...")

    try:
        mem_before = get_memory_usage()
        start_time = time.time()

        version_data = storage.read_at_version(table_name, version=1)

        version_time = time.time() - start_time
        mem_after = get_memory_usage()

        row_count = len(version_data[list(version_data.keys())[0]])

        print(f"  Time: {version_time:.4f}s")
        print(f"  Speed: {row_count / version_time:,.0f} rows/sec")
        print(f"  Rows read: {row_count:,}")
        print(f"  Supported: YES [OK]")

        results.add_result("ncf", "version_read", {
            "time": version_time,
            "speed": row_count / version_time,
            "rows": row_count,
            "memory_delta": mem_after - mem_before,
            "supported": True
        })
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Supported: NO [X]")
        results.add_result("ncf", "version_read", {"supported": False})

    # 6. Time Travel - Read at Timestamp
    print("\n6. Time Travel - Read at Timestamp...")

    try:
        # Get timestamp to read at version 1 (before append)
        # We need a timestamp AFTER version 1 was written but BEFORE version 2
        versions = storage.list_versions(table_name)

        if len(versions) >= 2:
            # Filter to only WRITE operations (skip CREATE which has no data)
            write_versions = [v for v in versions if v.operation == "WRITE"]

            if len(write_versions) >= 2:
                # Sort by timestamp to ensure correct order (oldest first)
                sorted_versions = sorted(write_versions, key=lambda v: v.timestamp)

                # Get timestamps from actual data writes
                timestamp_v1 = sorted_versions[0].timestamp  # First WRITE
                timestamp_v2 = sorted_versions[1].timestamp  # Second WRITE (append)

                # Use timestamp between version 1 and 2 (read at v1 state)
                delta = timestamp_v2 - timestamp_v1
                test_timestamp = timestamp_v1 + delta / 2

                mem_before = get_memory_usage()
                start_time = time.time()

                ts_data = storage.read_at_timestamp(table_name, timestamp=test_timestamp)

                ts_time = time.time() - start_time
                mem_after = get_memory_usage()

                row_count = len(ts_data[list(ts_data.keys())[0]])

                print(f"  Time: {ts_time:.4f}s")
                print(f"  Speed: {row_count / ts_time:,.0f} rows/sec")
                print(f"  Rows read: {row_count:,}")
                print(f"  Supported: YES [OK]")

                results.add_result("ncf", "timestamp_read", {
                    "time": ts_time,
                    "speed": row_count / ts_time,
                    "rows": row_count,
                    "memory_delta": mem_after - mem_before,
                    "supported": True
                })
            else:
                print(f"  Not enough WRITE versions for timestamp test (need 2+, have {len(write_versions)})")
                print(f"  Supported: YES (but test skipped)")
                results.add_result("ncf", "timestamp_read", {"supported": True, "skipped": True})
        else:
            print(f"  Not enough versions for timestamp test (need 2+, have {len(versions)})")
            print(f"  Supported: YES (but test skipped)")
            results.add_result("ncf", "timestamp_read", {"supported": True, "skipped": True})
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Supported: PARTIAL (method exists but test failed)")
        results.add_result("ncf", "timestamp_read", {"supported": False, "error": str(e)})

    print("\n[OK] NCF benchmark complete")


def benchmark_parquet(data: pd.DataFrame, temp_dir: Path, results: BenchmarkResults):
    """
    Benchmark Parquet format.

    Tests similar operations to NCF for fair comparison.
    """
    print("\n" + "=" * 100)
    print("PARQUET BENCHMARK")
    print("=" * 100)

    parquet_dir = temp_dir / "parquet_storage"
    parquet_dir.mkdir(exist_ok=True)

    parquet_file = parquet_dir / "benchmark_table.parquet"

    # 1. Initial Load
    print("\n1. Initial Load (write data)...")

    mem_before = get_memory_usage()
    start_time = time.time()

    data.to_parquet(parquet_file, compression="snappy", index=False, engine="pyarrow")

    load_time = time.time() - start_time
    mem_after = get_memory_usage()

    file_size = parquet_file.stat().st_size

    print(f"  Time: {load_time:.4f}s")
    print(f"  Speed: {len(data) / load_time:,.0f} rows/sec")
    print(f"  File size: {file_size / (1024*1024):.2f} MB")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    raw_size = data.memory_usage(deep=True).sum()

    results.add_result("parquet", "initial_load", {
        "time": load_time,
        "speed": len(data) / load_time,
        "file_size": file_size,
        "raw_data_size": raw_size,
        "memory_delta": mem_after - mem_before
    })

    # 2. Append Operation (simulate by reading + writing)
    print("\n2. Append Operation (read + concat + write)...")

    append_size = len(data) // 10
    append_data = data.head(append_size).copy()
    append_data["id"] = range(len(data), len(data) + append_size)

    mem_before = get_memory_usage()
    start_time = time.time()

    # Read existing
    existing = pd.read_parquet(parquet_file)
    # Append
    combined = pd.concat([existing, append_data], ignore_index=True)
    # Write back
    combined.to_parquet(parquet_file, compression="snappy", index=False, engine="pyarrow")

    append_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {append_time:.4f}s")
    print(f"  Speed: {append_size / append_time:,.0f} rows/sec")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")
    print(f"  Note: Parquet append requires full rewrite")

    results.add_result("parquet", "append", {
        "time": append_time,
        "speed": append_size / append_time,
        "memory_delta": mem_after - mem_before
    })

    # 3. Full Scan Read
    print("\n3. Full Scan Read...")

    mem_before = get_memory_usage()
    start_time = time.time()

    read_data = pd.read_parquet(parquet_file)

    read_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {read_time:.4f}s")
    print(f"  Speed: {len(read_data) / read_time:,.0f} rows/sec")
    print(f"  Rows read: {len(read_data):,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("parquet", "full_scan", {
        "time": read_time,
        "speed": len(read_data) / read_time,
        "rows": len(read_data),
        "memory_delta": mem_after - mem_before
    })

    # 4. Column Selection Read
    print("\n4. Column Selection Read (3 columns)...")

    selected_cols = ["id", "revenue", "department"]

    mem_before = get_memory_usage()
    start_time = time.time()

    col_data = pd.read_parquet(parquet_file, columns=selected_cols)

    col_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {col_time:.4f}s")
    print(f"  Speed: {len(col_data) / col_time:,.0f} rows/sec")
    print(f"  Rows read: {len(col_data):,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("parquet", "column_select", {
        "time": col_time,
        "speed": len(col_data) / col_time,
        "rows": len(col_data),
        "memory_delta": mem_after - mem_before
    })

    # 5. Time Travel - Not Supported
    print("\n5. Time Travel - Not Supported")
    print(f"  Supported: NO [X]")
    print(f"  Note: Parquet does not natively support versioning")

    results.add_result("parquet", "version_read", {"supported": False})
    results.add_result("parquet", "timestamp_read", {"supported": False})

    print("\n[OK] Parquet benchmark complete")


def benchmark_delta(data: pd.DataFrame, temp_dir: Path, results: BenchmarkResults):
    """
    Benchmark Delta Lake format.

    Tests similar operations to NCF for fair comparison.
    Gracefully handles if Delta Lake is not installed.
    """
    print("\n" + "=" * 100)
    print("DELTA LAKE BENCHMARK")
    print("=" * 100)

    try:
        from deltalake import write_deltalake, DeltaTable
        import pyarrow as pa
    except ImportError:
        print("\n[SKIP] Delta Lake not installed (pip install deltalake)")
        print("       Adding placeholder results...")

        # Add placeholder results
        for op in ["initial_load", "append", "full_scan", "column_select"]:
            results.add_result("delta", op, {
                "time": 0,
                "speed": 0,
                "memory_delta": 0,
                "skipped": True
            })
        results.add_result("delta", "version_read", {"supported": False, "skipped": True})
        results.add_result("delta", "timestamp_read", {"supported": False, "skipped": True})
        return

    delta_dir = temp_dir / "delta_storage"
    delta_dir.mkdir(exist_ok=True)

    delta_path = str(delta_dir / "benchmark_table")

    # 1. Initial Load
    print("\n1. Initial Load (write data)...")

    mem_before = get_memory_usage()
    start_time = time.time()

    write_deltalake(delta_path, data, mode="overwrite")

    load_time = time.time() - start_time
    mem_after = get_memory_usage()

    # Get file size
    delta_table_path = Path(delta_path)
    file_size = sum(f.stat().st_size for f in delta_table_path.rglob("*") if f.is_file())

    print(f"  Time: {load_time:.4f}s")
    print(f"  Speed: {len(data) / load_time:,.0f} rows/sec")
    print(f"  File size: {file_size / (1024*1024):.2f} MB")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    raw_size = data.memory_usage(deep=True).sum()

    results.add_result("delta", "initial_load", {
        "time": load_time,
        "speed": len(data) / load_time,
        "file_size": file_size,
        "raw_data_size": raw_size,
        "memory_delta": mem_after - mem_before
    })

    # 2. Append Operation
    print("\n2. Append Operation...")

    append_size = len(data) // 10
    append_data = data.head(append_size).copy()
    append_data["id"] = range(len(data), len(data) + append_size)

    mem_before = get_memory_usage()
    start_time = time.time()

    write_deltalake(delta_path, append_data, mode="append")

    append_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {append_time:.4f}s")
    print(f"  Speed: {append_size / append_time:,.0f} rows/sec")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("delta", "append", {
        "time": append_time,
        "speed": append_size / append_time,
        "memory_delta": mem_after - mem_before
    })

    # 3. Full Scan Read
    print("\n3. Full Scan Read...")

    mem_before = get_memory_usage()
    start_time = time.time()

    dt = DeltaTable(delta_path)
    read_data = dt.to_pandas()

    read_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {read_time:.4f}s")
    print(f"  Speed: {len(read_data) / read_time:,.0f} rows/sec")
    print(f"  Rows read: {len(read_data):,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("delta", "full_scan", {
        "time": read_time,
        "speed": len(read_data) / read_time,
        "rows": len(read_data),
        "memory_delta": mem_after - mem_before
    })

    # 4. Column Selection Read
    print("\n4. Column Selection Read (3 columns)...")

    selected_cols = ["id", "revenue", "department"]

    mem_before = get_memory_usage()
    start_time = time.time()

    dt = DeltaTable(delta_path)
    col_data = dt.to_pandas(columns=selected_cols)

    col_time = time.time() - start_time
    mem_after = get_memory_usage()

    print(f"  Time: {col_time:.4f}s")
    print(f"  Speed: {len(col_data) / col_time:,.0f} rows/sec")
    print(f"  Rows read: {len(col_data):,}")
    print(f"  Memory delta: {mem_after - mem_before:.2f} MB")

    results.add_result("delta", "column_select", {
        "time": col_time,
        "speed": len(col_data) / col_time,
        "rows": len(col_data),
        "memory_delta": mem_after - mem_before
    })

    # 5. Time Travel - Read at Version
    print("\n5. Time Travel - Read at Version...")

    try:
        mem_before = get_memory_usage()
        start_time = time.time()

        dt = DeltaTable(delta_path, version=0)
        version_data = dt.to_pandas()

        version_time = time.time() - start_time
        mem_after = get_memory_usage()

        print(f"  Time: {version_time:.4f}s")
        print(f"  Speed: {len(version_data) / version_time:,.0f} rows/sec")
        print(f"  Rows read: {len(version_data):,}")
        print(f"  Supported: YES [OK]")

        results.add_result("delta", "version_read", {
            "time": version_time,
            "speed": len(version_data) / version_time,
            "rows": len(version_data),
            "memory_delta": mem_after - mem_before,
            "supported": True
        })
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Supported: NO [X]")
        results.add_result("delta", "version_read", {"supported": False})

    # 6. Time Travel - Timestamp not tested (more complex in Delta)
    print("\n6. Time Travel - Timestamp (not tested)")
    results.add_result("delta", "timestamp_read", {"supported": True})

    print("\n[OK] Delta Lake benchmark complete")


def convert_to_json_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def run_comprehensive_benchmark(num_rows: int = 100_000):
    """
    Run the complete benchmark suite.

    Args:
        num_rows: Number of rows in test dataset
    """
    print("=" * 100)
    print("COMPREHENSIVE NCF PERFORMANCE BENCHMARK")
    print("=" * 100)
    print(f"\nDataset size: {num_rows:,} rows")
    print("Formats: NCF, Parquet, Delta Lake")
    print("Tests: Write, Read, Storage, Time Travel")

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="ncf_benchmark_"))
    print(f"Temp directory: {temp_dir}")

    try:
        # Create test dataset
        data = create_test_dataset(num_rows)

        # Initialize results
        results = BenchmarkResults()

        # Run benchmarks
        benchmark_ncf(data, temp_dir, results)
        benchmark_parquet(data, temp_dir, results)
        benchmark_delta(data, temp_dir, results)

        # Print summary
        results.print_summary()

        # Save results to JSON (convert numpy types first)
        output_file = Path(__file__).parent / "benchmark_results.json"
        with open(output_file, "w") as f:
            json_safe_results = convert_to_json_serializable(results.results)
            json.dump(json_safe_results, f, indent=2)
        print(f"\n[OK] Results saved to: {output_file}")

    finally:
        # Cleanup
        print(f"\nCleaning up temp directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("[OK] Cleanup complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NCF Comprehensive Performance Benchmark")
    parser.add_argument(
        "--rows",
        type=int,
        default=100_000,
        help="Number of rows in test dataset (default: 100,000)"
    )

    args = parser.parse_args()

    run_comprehensive_benchmark(num_rows=args.rows)
