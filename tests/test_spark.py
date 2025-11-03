"""
Comprehensive tests for NeuroLake Spark module.

Tests Spark configuration, session management, and I/O utilities.
Mocks PySpark where necessary to avoid requiring full Spark installation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pydantic import ValidationError
import pandas as pd
from neurolake.spark.config import SparkConfig, get_spark_config
from neurolake.spark.io import (
    SparkNCFReader,
    SparkNCFWriter,
    convert_parquet_to_ncf,
    convert_ncf_to_parquet,
)


# =============================================================================
# SparkConfig Tests
# =============================================================================

class TestSparkConfig:
    """Test SparkConfig configuration"""

    def test_default_values(self):
        """Test default Spark configuration values"""
        config = SparkConfig()
        assert config.app_name == "NeuroLake"
        assert config.executor_memory == "4g"
        assert config.driver_memory == "2g"
        assert config.executor_cores == 4
        assert config.driver_cores == 2
        assert config.dynamic_allocation_enabled is True
        assert config.aqe_enabled is True
        assert config.shuffle_partitions == 200
        assert config.compression_codec == "zstd"
        assert config.serializer == "org.apache.spark.serializer.KryoSerializer"

    def test_executor_cores_validation(self):
        """Test executor cores validation"""
        # Valid
        SparkConfig(executor_cores=1)
        SparkConfig(executor_cores=32)

        # Invalid
        with pytest.raises(ValidationError):
            SparkConfig(executor_cores=0)
        with pytest.raises(ValidationError):
            SparkConfig(executor_cores=33)

    def test_driver_cores_validation(self):
        """Test driver cores validation"""
        # Valid
        SparkConfig(driver_cores=1)
        SparkConfig(driver_cores=16)

        # Invalid
        with pytest.raises(ValidationError):
            SparkConfig(driver_cores=0)
        with pytest.raises(ValidationError):
            SparkConfig(driver_cores=17)

    def test_dynamic_allocation_settings(self):
        """Test dynamic allocation configuration"""
        config = SparkConfig(
            dynamic_allocation_enabled=True,
            dynamic_allocation_min_executors=2,
            dynamic_allocation_max_executors=20,
            dynamic_allocation_initial_executors=5
        )
        assert config.dynamic_allocation_enabled is True
        assert config.dynamic_allocation_min_executors == 2
        assert config.dynamic_allocation_max_executors == 20
        assert config.dynamic_allocation_initial_executors == 5

    def test_aqe_settings(self):
        """Test Adaptive Query Execution settings"""
        config = SparkConfig(
            aqe_enabled=True,
            aqe_coalesce_partitions_enabled=True,
            aqe_skew_join_enabled=True,
            aqe_skew_join_skewed_partition_factor=10.0
        )
        assert config.aqe_enabled is True
        assert config.aqe_coalesce_partitions_enabled is True
        assert config.aqe_skew_join_enabled is True
        assert config.aqe_skew_join_skewed_partition_factor == 10.0

    def test_s3_settings(self):
        """Test S3/MinIO configuration"""
        config = SparkConfig(
            s3_enabled=True,
            s3_endpoint="localhost:9000",
            s3_access_key="minioadmin",
            s3_secret_key="minioadmin",
            s3_path_style_access=True,
            s3_max_connections=50
        )
        assert config.s3_enabled is True
        assert config.s3_endpoint == "localhost:9000"
        assert config.s3_access_key == "minioadmin"
        assert config.s3_max_connections == 50

    def test_neurolake_optimizations(self):
        """Test NeuroLake-specific optimizations"""
        config = SparkConfig(
            neurolake_ncf_enabled=True,
            neurolake_cache_enabled=True,
            neurolake_pushdown_enabled=True,
            neurolake_vectorized_reader=True
        )
        assert config.neurolake_ncf_enabled is True
        assert config.neurolake_cache_enabled is True
        assert config.neurolake_pushdown_enabled is True
        assert config.neurolake_vectorized_reader is True

    def test_memory_fraction_validation(self):
        """Test memory fraction validation"""
        # Valid
        SparkConfig(memory_fraction=0.0)
        SparkConfig(memory_fraction=1.0)

        # Invalid
        with pytest.raises(ValidationError):
            SparkConfig(memory_fraction=-0.1)
        with pytest.raises(ValidationError):
            SparkConfig(memory_fraction=1.1)

    def test_ui_port_validation(self):
        """Test UI port validation"""
        # Valid
        SparkConfig(ui_port=1024)
        SparkConfig(ui_port=65535)

        # Invalid
        with pytest.raises(ValidationError):
            SparkConfig(ui_port=1023)
        with pytest.raises(ValidationError):
            SparkConfig(ui_port=65536)

    def test_to_spark_conf_basic(self):
        """Test basic Spark configuration conversion"""
        config = SparkConfig(
            app_name="TestApp",
            executor_memory="8g",
            executor_cores=8,
            driver_memory="4g",
            shuffle_partitions=400
        )
        conf = config.to_spark_conf()

        assert conf["spark.app.name"] == "TestApp"
        assert conf["spark.executor.memory"] == "8g"
        assert conf["spark.executor.cores"] == "8"
        assert conf["spark.driver.memory"] == "4g"
        assert conf["spark.sql.shuffle.partitions"] == "400"

    def test_to_spark_conf_s3_settings(self):
        """Test S3 configuration in Spark conf"""
        config = SparkConfig(
            s3_enabled=True,
            s3_endpoint="http://localhost:9000",
            s3_access_key="test_key",
            s3_secret_key="test_secret"
        )
        conf = config.to_spark_conf()

        assert "spark.hadoop.fs.s3a.impl" in conf
        assert conf["spark.hadoop.fs.s3a.endpoint"] == "http://localhost:9000"
        assert conf["spark.hadoop.fs.s3a.access.key"] == "test_key"
        assert conf["spark.hadoop.fs.s3a.secret.key"] == "test_secret"

    def test_to_spark_conf_delta_enabled(self):
        """Test Delta Lake configuration"""
        config = SparkConfig(delta_enabled=True)
        conf = config.to_spark_conf()

        assert "spark.sql.extensions" in conf
        assert "spark.sql.catalog.spark_catalog" in conf
        assert "DeltaSparkSessionExtension" in conf["spark.sql.extensions"]

    def test_to_spark_conf_extra_configs(self):
        """Test extra configurations"""
        config = SparkConfig(
            extra_configs={
                "spark.custom.setting": "value",
                "spark.another.setting": "123"
            }
        )
        conf = config.to_spark_conf()

        assert conf["spark.custom.setting"] == "value"
        assert conf["spark.another.setting"] == "123"

    def test_env_variable_loading(self, monkeypatch):
        """Test loading from environment variables"""
        monkeypatch.setenv("NEUROLAKE_SPARK_APP_NAME", "MyApp")
        monkeypatch.setenv("NEUROLAKE_SPARK_EXECUTOR_MEMORY", "16g")
        monkeypatch.setenv("NEUROLAKE_SPARK_EXECUTOR_CORES", "16")
        monkeypatch.setenv("NEUROLAKE_SPARK_SHUFFLE_PARTITIONS", "1000")

        config = SparkConfig()
        assert config.app_name == "MyApp"
        assert config.executor_memory == "16g"
        assert config.executor_cores == 16
        assert config.shuffle_partitions == 1000

    def test_boolean_config_conversion(self):
        """Test boolean values are converted to string properly"""
        config = SparkConfig(
            dynamic_allocation_enabled=True,
            aqe_enabled=False
        )
        conf = config.to_spark_conf()

        assert conf["spark.dynamicAllocation.enabled"] == "true"
        assert conf["spark.sql.adaptive.enabled"] == "false"


class TestGetSparkConfig:
    """Test get_spark_config function"""

    def test_get_spark_config_singleton(self):
        """Test get_spark_config returns singleton"""
        # Import the module to reset global state
        from neurolake.spark import config as spark_config_module
        spark_config_module._spark_config = None

        config1 = get_spark_config()
        config2 = get_spark_config()
        assert config1 is config2


# =============================================================================
# SparkSession Tests (Mocked)
# =============================================================================

class TestSparkSessionFactory:
    """Test SparkSessionFactory with mocked PySpark"""

    @pytest.fixture
    def mock_spark_session(self):
        """Create a mock Spark session"""
        mock_session = MagicMock()
        mock_session.sparkContext = MagicMock()
        mock_session.sparkContext.setLogLevel = MagicMock()
        mock_session.stop = MagicMock()
        return mock_session

    @pytest.fixture
    def mock_spark_builder(self, mock_spark_session):
        """Create a mock Spark builder"""
        mock_builder = MagicMock()
        mock_builder.config = MagicMock(return_value=mock_builder)
        mock_builder.enableHiveSupport = MagicMock(return_value=mock_builder)
        mock_builder.getOrCreate = MagicMock(return_value=mock_spark_session)
        return mock_builder

    @patch('neurolake.spark.session.SparkSession')
    @patch('neurolake.spark.session.SparkConf')
    def test_get_session_creates_session(
        self,
        mock_conf_class,
        mock_session_class,
        mock_spark_builder,
        mock_spark_session
    ):
        """Test get_session creates Spark session"""
        from neurolake.spark.session import SparkSessionFactory

        # Setup mocks
        mock_conf = MagicMock()
        mock_conf_class.return_value = mock_conf
        mock_session_class.builder = mock_spark_builder

        # Create factory and get session
        factory = SparkSessionFactory()
        factory._spark = None  # Reset singleton

        session = factory.get_session()

        # Verify session was created
        assert session is not None
        mock_spark_builder.getOrCreate.assert_called_once()

    @patch('neurolake.spark.session.SparkSession')
    def test_get_session_reuses_existing(
        self,
        mock_session_class,
        mock_spark_session
    ):
        """Test get_session reuses existing session"""
        from neurolake.spark.session import SparkSessionFactory

        factory = SparkSessionFactory()
        factory._spark = mock_spark_session

        session = factory.get_session()

        assert session is mock_spark_session
        # Should not create new session
        mock_session_class.builder.getOrCreate.assert_not_called()

    @patch('neurolake.spark.session.SparkSession')
    def test_get_session_force_recreate(
        self,
        mock_session_class,
        mock_spark_builder,
        mock_spark_session
    ):
        """Test force recreate stops and recreates session"""
        from neurolake.spark.session import SparkSessionFactory

        mock_session_class.builder = mock_spark_builder

        factory = SparkSessionFactory()
        old_session = MagicMock()
        old_session.stop = MagicMock()
        factory._spark = old_session

        session = factory.get_session(force_recreate=True)

        old_session.stop.assert_called_once()
        mock_spark_builder.getOrCreate.assert_called_once()

    def test_stop_session(self, mock_spark_session):
        """Test stopping Spark session"""
        from neurolake.spark.session import SparkSessionFactory

        factory = SparkSessionFactory()
        factory._spark = mock_spark_session

        factory.stop()

        mock_spark_session.stop.assert_called_once()
        assert factory._spark is None

    def test_is_active_property(self, mock_spark_session):
        """Test is_active property"""
        from neurolake.spark.session import SparkSessionFactory

        factory = SparkSessionFactory()

        factory._spark = None
        assert factory.is_active is False

        factory._spark = mock_spark_session
        assert factory.is_active is True


# =============================================================================
# SparkNCFReader Tests
# =============================================================================

class TestSparkNCFReader:
    """Test SparkNCFReader"""

    def test_init_without_spark(self):
        """Test initialization without Spark session"""
        reader = SparkNCFReader()
        assert reader.spark is None

    def test_init_with_spark(self):
        """Test initialization with Spark session"""
        mock_spark = MagicMock()
        reader = SparkNCFReader(mock_spark)
        assert reader.spark is mock_spark

    @patch('neurolake.spark.io.pd.read_parquet')
    def test_read_parquet_without_spark(self, mock_read_parquet):
        """Test reading Parquet without Spark"""
        mock_df = pd.DataFrame({"a": [1, 2, 3]})
        mock_read_parquet.return_value = mock_df

        reader = SparkNCFReader()
        result = reader.read_parquet("test.parquet")

        mock_read_parquet.assert_called_once_with("test.parquet")
        assert isinstance(result, pd.DataFrame)

    def test_read_parquet_with_spark(self):
        """Test reading Parquet with Spark"""
        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_spark.read.parquet.return_value = mock_df

        reader = SparkNCFReader(mock_spark)
        result = reader.read_parquet("s3a://bucket/test.parquet")

        mock_spark.read.parquet.assert_called_once_with("s3a://bucket/test.parquet")
        assert result is mock_df

    @pytest.mark.skip(reason="NCF integration tested separately in test_ncf.py")
    def test_read_ncf_without_spark(self):
        """Test reading NCF without Spark (Python fallback)"""
        # This is an integration test - NCF module has its own tests
        pass

    def test_read_ncf_with_spark_not_implemented(self):
        """Test reading NCF with Spark raises NotImplementedError"""
        mock_spark = MagicMock()
        reader = SparkNCFReader(mock_spark)

        with pytest.raises(NotImplementedError):
            reader.read_ncf("test.ncf")


# =============================================================================
# SparkNCFWriter Tests
# =============================================================================

class TestSparkNCFWriter:
    """Test SparkNCFWriter"""

    def test_init_without_spark(self):
        """Test initialization without Spark session"""
        writer = SparkNCFWriter()
        assert writer.spark is None

    def test_init_with_spark(self):
        """Test initialization with Spark session"""
        mock_spark = MagicMock()
        writer = SparkNCFWriter(mock_spark)
        assert writer.spark is mock_spark

    @pytest.mark.skip(reason="NCF integration tested separately in test_ncf.py")
    def test_write_ncf_without_spark(self):
        """Test writing NCF without Spark"""
        # This is an integration test - NCF module has its own tests
        pass

    def test_write_ncf_with_spark_not_implemented(self):
        """Test writing NCF with Spark raises NotImplementedError"""
        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_df.write = MagicMock()

        writer = SparkNCFWriter(mock_spark)

        with pytest.raises(NotImplementedError):
            writer.write_ncf(mock_df, "output.ncf")

    def test_write_parquet_without_spark(self):
        """Test writing Parquet without Spark"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        df.to_parquet = MagicMock()

        writer = SparkNCFWriter()
        writer.write_parquet(df, "output.parquet", compression="snappy")

        df.to_parquet.assert_called_once_with("output.parquet", compression="snappy")

    def test_write_parquet_with_spark(self):
        """Test writing Parquet with Spark"""
        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_write = MagicMock()
        mock_mode = MagicMock()
        mock_write.mode.return_value = mock_mode
        mock_df.write = mock_write

        writer = SparkNCFWriter(mock_spark)
        writer.write_parquet(mock_df, "s3a://bucket/output.parquet", mode="append", compression="zstd")

        mock_write.mode.assert_called_once_with("append")
        mock_mode.parquet.assert_called_once_with("s3a://bucket/output.parquet", compression="zstd")

    @pytest.mark.skip(reason="NCF integration tested separately in test_ncf.py")
    def test_write_ncf_converts_spark_df_to_pandas(self):
        """Test writing NCF converts Spark DataFrame to pandas"""
        # This is an integration test - NCF module has its own tests
        pass


# =============================================================================
# Conversion Functions Tests
# =============================================================================

class TestConversionFunctions:
    """Test Parquet/NCF conversion functions"""

    @patch('neurolake.spark.io.SparkNCFWriter')
    @patch('neurolake.spark.io.SparkNCFReader')
    def test_convert_parquet_to_ncf_with_spark(self, mock_reader_class, mock_writer_class):
        """Test converting Parquet to NCF with Spark"""
        # Setup mocks
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_writer_class.return_value = mock_writer

        mock_df = MagicMock()
        mock_df.count.return_value = 1000
        mock_reader.read_parquet.return_value = mock_df

        # Convert
        result = convert_parquet_to_ncf(
            "input.parquet",
            "output.ncf",
            spark_session=MagicMock(),
            compression_level=5
        )

        # Verify
        mock_reader.read_parquet.assert_called_once_with("input.parquet")
        mock_writer.write_ncf.assert_called_once_with(mock_df, "output.ncf", compression_level=5)
        assert result["row_count"] == 1000
        assert result["input_path"] == "input.parquet"
        assert result["output_path"] == "output.ncf"

    @pytest.mark.skip(reason="NCF integration tested separately")
    def test_convert_parquet_to_ncf_without_spark(self):
        """Test converting Parquet to NCF without Spark"""
        # This is an integration test involving NCF - tested separately
        pass

    @patch('neurolake.spark.io.SparkNCFWriter')
    @patch('neurolake.spark.io.SparkNCFReader')
    def test_convert_ncf_to_parquet_with_spark(self, mock_reader_class, mock_writer_class):
        """Test converting NCF to Parquet with Spark"""
        # Setup mocks
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_writer_class.return_value = mock_writer

        mock_df = MagicMock()
        mock_df.count.return_value = 5000
        mock_reader.read_ncf.return_value = mock_df

        # Convert
        result = convert_ncf_to_parquet(
            "input.ncf",
            "output.parquet",
            spark_session=MagicMock(),
            compression="snappy"
        )

        # Verify
        mock_reader.read_ncf.assert_called_once_with("input.ncf")
        mock_writer.write_parquet.assert_called_once_with(mock_df, "output.parquet", compression="snappy")
        assert result["row_count"] == 5000
        assert result["compression"] == "snappy"

    @pytest.mark.skip(reason="NCF integration tested separately")
    def test_convert_ncf_to_parquet_without_spark(self):
        """Test converting NCF to Parquet without Spark"""
        # This is an integration test involving NCF - tested separately
        pass


# =============================================================================
# Integration Tests
# =============================================================================

class TestSparkIntegration:
    """Integration tests for Spark module"""

    def test_spark_config_to_session_config(self):
        """Test Spark config can be converted to session config"""
        config = SparkConfig(
            app_name="IntegrationTest",
            executor_memory="8g",
            s3_enabled=True,
            s3_endpoint="localhost:9000",
            delta_enabled=True
        )

        conf_dict = config.to_spark_conf()

        # Verify key configurations
        assert conf_dict["spark.app.name"] == "IntegrationTest"
        assert conf_dict["spark.executor.memory"] == "8g"
        assert "spark.hadoop.fs.s3a.endpoint" in conf_dict
        assert "spark.sql.extensions" in conf_dict

    def test_reader_writer_compatibility(self):
        """Test reader and writer can work together"""
        # Create reader and writer
        reader = SparkNCFReader(None)
        writer = SparkNCFWriter(None)

        # They should be compatible for pandas operations
        assert reader.spark is None
        assert writer.spark is None


# =============================================================================
# Edge Cases
# =============================================================================

class TestSparkEdgeCases:
    """Test edge cases and error handling"""

    def test_spark_config_with_none_values(self):
        """Test Spark config with None values"""
        config = SparkConfig(
            executor_instances=None,
            s3_endpoint=None,
            s3_access_key=None
        )
        assert config.executor_instances is None
        assert config.s3_endpoint is None

    def test_spark_config_empty_extra_configs(self):
        """Test Spark config with empty extra configs"""
        config = SparkConfig(extra_configs={})
        conf = config.to_spark_conf()
        assert isinstance(conf, dict)

    def test_spark_config_s3_disabled(self):
        """Test S3 configuration when disabled"""
        config = SparkConfig(s3_enabled=False, s3_endpoint="localhost:9000")
        conf = config.to_spark_conf()
        assert "spark.hadoop.fs.s3a.impl" not in conf

    def test_spark_config_delta_disabled(self):
        """Test Delta configuration when disabled"""
        config = SparkConfig(delta_enabled=False)
        conf = config.to_spark_conf()
        assert "spark.sql.extensions" not in conf

    def test_memory_string_formats(self):
        """Test different memory string formats"""
        config1 = SparkConfig(executor_memory="4g")
        config2 = SparkConfig(executor_memory="4096m")
        config3 = SparkConfig(driver_memory="2048m")

        assert config1.executor_memory == "4g"
        assert config2.executor_memory == "4096m"
        assert config3.driver_memory == "2048m"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
