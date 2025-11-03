"""Test Spark session creation and configuration"""

import pytest
from neurolake.spark import get_spark_session, get_spark_config, stop_spark_session


def test_spark_config_creation():
    """Test SparkConfig can be created with defaults"""
    config = get_spark_config()
    
    assert config.app_name == "NeuroLake"
    assert config.executor_memory == "4g"
    assert config.driver_memory == "2g"
    assert config.aqe_enabled is True
    assert config.dynamic_allocation_enabled is True
    assert config.s3_enabled is True
    assert config.delta_enabled is True


def test_spark_config_to_dict():
    """Test SparkConfig converts to Spark configuration dict"""
    config = get_spark_config()
    conf_dict = config.to_spark_conf()
    
    assert "spark.app.name" in conf_dict
    assert conf_dict["spark.app.name"] == "NeuroLake"
    assert "spark.executor.memory" in conf_dict
    assert "spark.driver.memory" in conf_dict
    assert "spark.sql.adaptive.enabled" in conf_dict
    assert conf_dict["spark.sql.adaptive.enabled"] == "true"


@pytest.mark.skipif(
    True,  # Skip by default as it requires Java/Spark installation
    reason="Requires Spark installation - enable manually for integration tests"
)
def test_spark_session_creation():
    """Test Spark session can be created (requires Spark installed)"""
    try:
        spark = get_spark_session()
        
        assert spark is not None
        assert spark.version is not None
        
        # Test that we can access SparkContext
        assert spark.sparkContext is not None
        
        # Clean up
        stop_spark_session()
        
    except Exception as e:
        pytest.fail(f"Failed to create Spark session: {e}")


def test_spark_session_singleton():
    """Test that get_spark_session returns same instance (without actual Spark)"""
    # This just tests the factory pattern, not actual Spark
    from neurolake.spark.session import SparkSessionFactory
    
    factory1 = SparkSessionFactory()
    factory2 = SparkSessionFactory()
    
    # Should be same instance (singleton)
    assert factory1 is factory2


if __name__ == "__main__":
    # Run basic config tests
    print("Testing SparkConfig...")
    test_spark_config_creation()
    print("[PASS] SparkConfig creation works")

    test_spark_config_to_dict()
    print("[PASS] SparkConfig to_spark_conf() works")

    test_spark_session_singleton()
    print("[PASS] SparkSessionFactory singleton works")

    print("\n[SUCCESS] All tests passed!")
