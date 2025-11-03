"""
NeuroLake Spark I/O Utilities

Utilities for reading and writing NCF and Parquet files with Spark.
Supports S3/MinIO storage and local filesystem.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import pandas as pd


class SparkNCFReader:
    """
    Read NCF files with Spark (or fallback to Python).
    
    When Spark is available, uses Spark DataFrames.
    Otherwise, falls back to Python implementation.
    """
    
    def __init__(self, spark_session=None):
        self.spark = spark_session
        
    def read_ncf(self, path: str) -> Any:
        """
        Read NCF file.
        
        Args:
            path: Path to NCF file (local or s3a://)
            
        Returns:
            Spark DataFrame or pandas DataFrame
        """
        if self.spark is not None:
            # Use Spark to read NCF
            # TODO: Implement NCF DataSource for Spark
            raise NotImplementedError("Spark NCF DataSource not yet implemented")
        else:
            # Fallback to Python NCF reader
            from neurolake.ncf import NCFReader
            reader = NCFReader(path)
            data = reader.read()
            return pd.DataFrame(data)
    
    def read_parquet(self, path: str) -> Any:
        """
        Read Parquet file.
        
        Args:
            path: Path to Parquet file (local or s3a://)
            
        Returns:
            Spark DataFrame or pandas DataFrame
        """
        if self.spark is not None:
            return self.spark.read.parquet(path)
        else:
            return pd.read_parquet(path)


class SparkNCFWriter:
    """
    Write NCF files with Spark (or fallback to Python).
    """
    
    def __init__(self, spark_session=None):
        self.spark = spark_session
        
    def write_ncf(
        self,
        df: Any,
        path: str,
        mode: str = "overwrite",
        compression_level: int = 3
    ):
        """
        Write NCF file.
        
        Args:
            df: DataFrame to write (Spark or pandas)
            path: Output path (local or s3a://)
            mode: Write mode (overwrite, append)
            compression_level: Compression level (1-22)
        """
        if self.spark is not None and hasattr(df, 'write'):
            # Spark DataFrame
            # TODO: Implement NCF DataSource for Spark
            raise NotImplementedError("Spark NCF DataSource not yet implemented")
        else:
            # pandas DataFrame - use Python NCF writer
            from neurolake.ncf import NCFWriter
            
            if not isinstance(df, pd.DataFrame):
                # Convert Spark DataFrame to pandas
                df = df.toPandas()
            
            writer = NCFWriter(path)
            writer.write(df, compression_level=compression_level)
    
    def write_parquet(
        self,
        df: Any,
        path: str,
        mode: str = "overwrite",
        compression: str = "zstd"
    ):
        """
        Write Parquet file.
        
        Args:
            df: DataFrame to write
            path: Output path
            mode: Write mode
            compression: Compression codec
        """
        if self.spark is not None and hasattr(df, 'write'):
            df.write.mode(mode).parquet(path, compression=compression)
        else:
            df.to_parquet(path, compression=compression)


def convert_parquet_to_ncf(
    input_path: str,
    output_path: str,
    spark_session=None,
    compression_level: int = 3
) -> Dict[str, Any]:
    """
    Convert Parquet file to NCF format.
    
    Args:
        input_path: Input Parquet path
        output_path: Output NCF path
        spark_session: Optional Spark session
        compression_level: NCF compression level
        
    Returns:
        Dict with conversion statistics
    """
    reader = SparkNCFReader(spark_session)
    writer = SparkNCFWriter(spark_session)
    
    # Read Parquet
    df = reader.read_parquet(input_path)
    
    # Get row count
    if hasattr(df, 'count'):
        row_count = df.count()  # Spark
    else:
        row_count = len(df)  # pandas
    
    # Write NCF
    writer.write_ncf(df, output_path, compression_level=compression_level)
    
    return {
        "input_path": input_path,
        "output_path": output_path,
        "row_count": row_count,
        "compression_level": compression_level,
    }


def convert_ncf_to_parquet(
    input_path: str,
    output_path: str,
    spark_session=None,
    compression: str = "zstd"
) -> Dict[str, Any]:
    """
    Convert NCF file to Parquet format.
    
    Args:
        input_path: Input NCF path
        output_path: Output Parquet path
        spark_session: Optional Spark session
        compression: Parquet compression codec
        
    Returns:
        Dict with conversion statistics
    """
    reader = SparkNCFReader(spark_session)
    writer = SparkNCFWriter(spark_session)
    
    # Read NCF
    df = reader.read_ncf(input_path)
    
    # Get row count
    if hasattr(df, 'count'):
        row_count = df.count()  # Spark
    else:
        row_count = len(df)  # pandas
    
    # Write Parquet
    writer.write_parquet(df, output_path, compression=compression)
    
    return {
        "input_path": input_path,
        "output_path": output_path,
        "row_count": row_count,
        "compression": compression,
    }


__all__ = [
    "SparkNCFReader",
    "SparkNCFWriter",
    "convert_parquet_to_ncf",
    "convert_ncf_to_parquet",
]
