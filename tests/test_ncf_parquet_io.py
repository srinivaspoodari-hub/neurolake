"""Test NCF and Parquet I/O operations"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
import os


def create_test_dataframe(rows: int = 1000) -> pd.DataFrame:
    """Create test DataFrame with various data types."""
    np.random.seed(42)
    
    return pd.DataFrame({
        'id': np.arange(rows),
        'value': np.random.randn(rows),
        'category': np.random.choice(['A', 'B', 'C', 'D'], rows),
        'score': np.random.randint(0, 100, rows),
        'flag': np.random.choice([True, False], rows),
    })


def test_parquet_write_read():
    """Test writing and reading Parquet files."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        df = create_test_dataframe(1000)
        parquet_path = temp_dir / "test.parquet"
        
        # Write Parquet
        df.to_parquet(parquet_path, compression='zstd')
        
        # Read back
        df_read = pd.read_parquet(parquet_path)
        
        # Verify
        assert len(df_read) == len(df)
        assert list(df_read.columns) == list(df.columns)
        
        print("[PASS] Parquet write/read works")
        
    finally:
        shutil.rmtree(temp_dir)


def test_compression_formats():
    """Test different compression formats."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        df = create_test_dataframe(1000)
        compressions = ['zstd', 'snappy', 'gzip']
        
        for compression in compressions:
            path = temp_dir / f"test_{compression}.parquet"
            df.to_parquet(path, compression=compression)
            df_read = pd.read_parquet(path)
            assert len(df_read) == 1000
        
        print("[PASS] All compression formats work")
        
    finally:
        shutil.rmtree(temp_dir)


def test_file_sizes():
    """Compare file sizes of different formats."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        df = create_test_dataframe(1000)
        
        parquet_zstd = temp_dir / "test_zstd.parquet"
        parquet_snappy = temp_dir / "test_snappy.parquet"
        parquet_gzip = temp_dir / "test_gzip.parquet"
        
        # Write with different compressions
        df.to_parquet(parquet_zstd, compression='zstd')
        df.to_parquet(parquet_snappy, compression='snappy')
        df.to_parquet(parquet_gzip, compression='gzip')
        
        # Get sizes
        size_zstd = os.path.getsize(parquet_zstd)
        size_snappy = os.path.getsize(parquet_snappy)
        size_gzip = os.path.getsize(parquet_gzip)
        
        print(f"\nFile sizes (1000 rows):")
        print(f"  Zstd:   {size_zstd:,} bytes")
        print(f"  Snappy: {size_snappy:,} bytes")
        print(f"  Gzip:   {size_gzip:,} bytes")
        
        print("[PASS] File size comparison complete")
        
    finally:
        shutil.rmtree(temp_dir)


def test_large_dataset():
    """Test with larger dataset."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create larger DataFrame
        large_df = create_test_dataframe(100000)  # 100K rows
        parquet_path = temp_dir / "large.parquet"
        
        # Write
        large_df.to_parquet(parquet_path, compression='zstd')
        
        # Read
        df_read = pd.read_parquet(parquet_path)
        
        # Verify
        assert len(df_read) == 100000
        
        size = os.path.getsize(parquet_path)
        print(f"[PASS] Large dataset: 100K rows, {size:,} bytes")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("=== NCF and Parquet I/O Tests ===\n")
    
    test_parquet_write_read()
    test_compression_formats()
    test_file_sizes()
    test_large_dataset()
    
    print("\n[SUCCESS] All I/O tests passed!")
