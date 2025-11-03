"""
NeuroLake Spark Session Factory

Singleton factory for creating and managing Spark sessions with NeuroLake optimizations.
"""

from typing import Optional
import threading
from pyspark.sql import SparkSession
from pyspark import SparkConf

from neurolake.spark.config import SparkConfig, get_spark_config
from neurolake.config import get_settings


class SparkSessionFactory:
    """
    Singleton factory for Spark session management.
    
    Creates optimized Spark sessions with:
    - NeuroLake-specific configurations
    - S3/MinIO integration
    - Delta Lake support
    - Adaptive Query Execution
    - Memory optimization
    """

    _instance: Optional["SparkSessionFactory"] = None
    _lock = threading.Lock()
    _spark: Optional[SparkSession] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_session(
        self,
        spark_config: Optional[SparkConfig] = None,
        force_recreate: bool = False
    ) -> SparkSession:
        """
        Get or create Spark session.
        
        Args:
            spark_config: Custom Spark configuration (uses default if None)
            force_recreate: Force recreation of Spark session
            
        Returns:
            SparkSession: Configured Spark session
        """
        if force_recreate and self._spark is not None:
            self._spark.stop()
            self._spark = None

        if self._spark is not None:
            return self._spark

        with self._lock:
            if self._spark is None:
                self._spark = self._create_session(spark_config)

        return self._spark

    def _create_session(self, spark_config: Optional[SparkConfig] = None) -> SparkSession:
        """
        Create new Spark session with NeuroLake configuration.
        
        Args:
            spark_config: Spark configuration
            
        Returns:
            SparkSession: Configured Spark session
        """
        if spark_config is None:
            spark_config = get_spark_config()

        # Get NeuroLake settings
        settings = get_settings()

        # Override S3 settings from NeuroLake config if not set
        if spark_config.s3_enabled:
            if spark_config.s3_endpoint is None:
                endpoint = settings.storage.endpoint
                if not endpoint.startswith("http"):
                    protocol = "https" if settings.storage.secure else "http"
                    spark_config.s3_endpoint = f"{protocol}://{endpoint}"
                else:
                    spark_config.s3_endpoint = endpoint

            if spark_config.s3_access_key is None:
                spark_config.s3_access_key = settings.storage.access_key

            if spark_config.s3_secret_key is None:
                spark_config.s3_secret_key = settings.storage.secret_key

        # Get Spark configuration dict
        conf_dict = spark_config.to_spark_conf()

        # Create SparkConf
        conf = SparkConf()
        for key, value in conf_dict.items():
            conf.set(key, value)

        # Build Spark session
        builder = SparkSession.builder.config(conf=conf)

        # Add JAR packages if needed
        if spark_config.s3_enabled or spark_config.delta_enabled:
            packages = []
            if spark_config.s3_enabled:
                packages.extend([
                    "org.apache.hadoop:hadoop-aws:3.3.4",
                    "com.amazonaws:aws-java-sdk-bundle:1.12.262"
                ])
            if spark_config.delta_enabled:
                packages.append("io.delta:delta-spark_2.12:3.0.0")
            
            builder = builder.config("spark.jars.packages", ",".join(packages))

        # Enable Hive support
        builder = builder.enableHiveSupport()

        # Create session
        spark = builder.getOrCreate()

        # Set log level
        spark.sparkContext.setLogLevel(spark_config.log_level)

        return spark

    def stop(self):
        """Stop the Spark session."""
        if self._spark is not None:
            self._spark.stop()
            self._spark = None

    @property
    def is_active(self) -> bool:
        """Check if Spark session is active."""
        return self._spark is not None


# Global factory instance
_factory: Optional[SparkSessionFactory] = None


def get_spark_session(
    spark_config: Optional[SparkConfig] = None,
    force_recreate: bool = False
) -> SparkSession:
    """
    Get or create Spark session (convenience function).
    
    Args:
        spark_config: Custom Spark configuration
        force_recreate: Force recreation of session
        
    Returns:
        SparkSession: Configured Spark session
        
    Example:
        >>> from neurolake.spark import get_spark_session
        >>> spark = get_spark_session()
        >>> df = spark.read.parquet("s3a://data/file.parquet")
    """
    global _factory
    if _factory is None:
        _factory = SparkSessionFactory()
    return _factory.get_session(spark_config, force_recreate)


def stop_spark_session():
    """Stop the global Spark session."""
    global _factory
    if _factory is not None:
        _factory.stop()


__all__ = [
    "SparkSessionFactory",
    "get_spark_session",
    "stop_spark_session",
]
