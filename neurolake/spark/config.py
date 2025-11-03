"""
NeuroLake Spark Configuration

Optimized Spark configuration for NeuroLake with:
- Memory optimization for executor and driver
- Adaptive Query Execution (AQE) enabled
- NeuroLake-specific optimizations  
- S3/MinIO integration
- NCF format support
"""

from typing import Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SparkConfig(BaseSettings):
    """Spark configuration optimized for NeuroLake workloads."""

    model_config = SettingsConfigDict(
        env_prefix="NEUROLAKE_SPARK_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="NeuroLake", description="Spark application name")
    
    # Executor Memory
    executor_memory: str = Field(default="4g", description="Executor memory")
    executor_memory_overhead: str = Field(default="1g", description="Executor memory overhead")
    executor_cores: int = Field(default=4, ge=1, le=32)
    executor_instances: Optional[int] = Field(default=None, ge=1)

    # Driver Memory
    driver_memory: str = Field(default="2g", description="Driver memory")
    driver_memory_overhead: str = Field(default="512m", description="Driver memory overhead")
    driver_cores: int = Field(default=2, ge=1, le=16)
    driver_max_result_size: str = Field(default="2g")

    # Dynamic Allocation
    dynamic_allocation_enabled: bool = Field(default=True)
    dynamic_allocation_min_executors: int = Field(default=1, ge=0)
    dynamic_allocation_max_executors: int = Field(default=10, ge=1)
    dynamic_allocation_initial_executors: int = Field(default=2, ge=1)

    # Adaptive Query Execution (AQE)
    aqe_enabled: bool = Field(default=True, description="Enable AQE")
    aqe_coalesce_partitions_enabled: bool = Field(default=True)
    aqe_coalesce_partitions_min_partition_size: str = Field(default="1mb")
    aqe_skew_join_enabled: bool = Field(default=True)
    aqe_skew_join_skewed_partition_factor: float = Field(default=5.0, ge=1.0)
    aqe_skew_join_skewed_partition_threshold: str = Field(default="256mb")

    # Shuffle
    shuffle_partitions: int = Field(default=200, ge=1)
    shuffle_compress: bool = Field(default=True)
    
    # Compression
    compression_codec: str = Field(default="zstd")
    serializer: str = Field(default="org.apache.spark.serializer.KryoSerializer")

    # NeuroLake Optimizations
    neurolake_ncf_enabled: bool = Field(default=True)
    neurolake_cache_enabled: bool = Field(default=True)
    neurolake_pushdown_enabled: bool = Field(default=True)
    neurolake_vectorized_reader: bool = Field(default=True)

    # S3/MinIO
    s3_enabled: bool = Field(default=True)
    s3_endpoint: Optional[str] = Field(default=None)
    s3_access_key: Optional[str] = Field(default=None)
    s3_secret_key: Optional[str] = Field(default=None)
    s3_path_style_access: bool = Field(default=True)
    s3_ssl_enabled: bool = Field(default=False)
    s3_max_connections: int = Field(default=100, ge=1, le=1000)

    # SQL
    sql_autoBroadcastJoinThreshold: str = Field(default="10mb")
    sql_files_maxPartitionBytes: str = Field(default="128mb")

    # Delta Lake
    delta_enabled: bool = Field(default=True)
    
    # Monitoring
    log_level: str = Field(default="WARN")
    ui_enabled: bool = Field(default=True)
    ui_port: int = Field(default=4040, ge=1024, le=65535)

    # Performance
    speculation_enabled: bool = Field(default=True)
    memory_fraction: float = Field(default=0.6, ge=0.0, le=1.0)
    memory_storage_fraction: float = Field(default=0.5, ge=0.0, le=1.0)

    extra_configs: Dict[str, str] = Field(default_factory=dict)

    def to_spark_conf(self) -> Dict[str, str]:
        conf = {}
        conf["spark.app.name"] = self.app_name
        conf["spark.executor.memory"] = self.executor_memory
        conf["spark.executor.memoryOverhead"] = self.executor_memory_overhead
        conf["spark.executor.cores"] = str(self.executor_cores)
        conf["spark.driver.memory"] = self.driver_memory
        conf["spark.driver.cores"] = str(self.driver_cores)
        conf["spark.dynamicAllocation.enabled"] = str(self.dynamic_allocation_enabled).lower()
        conf["spark.sql.adaptive.enabled"] = str(self.aqe_enabled).lower()
        conf["spark.sql.shuffle.partitions"] = str(self.shuffle_partitions)
        conf["spark.serializer"] = self.serializer
        
        if self.s3_enabled:
            conf["spark.hadoop.fs.s3a.impl"] = "org.apache.hadoop.fs.s3a.S3AFileSystem"
            if self.s3_endpoint:
                conf["spark.hadoop.fs.s3a.endpoint"] = self.s3_endpoint
            if self.s3_access_key:
                conf["spark.hadoop.fs.s3a.access.key"] = self.s3_access_key
            if self.s3_secret_key:
                conf["spark.hadoop.fs.s3a.secret.key"] = self.s3_secret_key
                
        if self.delta_enabled:
            conf["spark.sql.extensions"] = "io.delta.sql.DeltaSparkSessionExtension"
            conf["spark.sql.catalog.spark_catalog"] = "org.apache.spark.sql.delta.catalog.DeltaCatalog"
            
        conf.update(self.extra_configs)
        return conf


_spark_config: Optional[SparkConfig] = None

def get_spark_config() -> SparkConfig:
    global _spark_config
    if _spark_config is None:
        _spark_config = SparkConfig()
    return _spark_config

__all__ = ["SparkConfig", "get_spark_config"]
