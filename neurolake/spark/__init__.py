"""
NeuroLake Spark Integration

Provides optimized Spark session management with:
- Adaptive Query Execution (AQE)
- S3/MinIO integration
- Delta Lake support
- NeuroLake NCF format support
- Memory optimization

Example:
    from neurolake.spark import get_spark_session

    spark = get_spark_session()
    df = spark.read.parquet("s3a://data/file.parquet")
"""

from neurolake.spark.config import SparkConfig, get_spark_config
from neurolake.spark.session import (
    SparkSessionFactory,
    get_spark_session,
    stop_spark_session,
)
from neurolake.spark.io import (
    SparkNCFReader,
    SparkNCFWriter,
    convert_parquet_to_ncf,
    convert_ncf_to_parquet,
)

__all__ = [
    "SparkConfig",
    "get_spark_config",
    "SparkSessionFactory",
    "get_spark_session",
    "stop_spark_session",
    "SparkNCFReader",
    "SparkNCFWriter",
    "convert_parquet_to_ncf",
    "convert_ncf_to_parquet",
]
