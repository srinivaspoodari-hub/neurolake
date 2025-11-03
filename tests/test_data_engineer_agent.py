"""
Tests for DataEngineerAgent
"""

import pytest
from unittest.mock import Mock

from neurolake.agents import (
    DataEngineerAgent,
    Pipeline,
    Transformation,
    PipelineStage,
    TransformationType
)


# ===== Basic Setup Tests =====

def test_data_engineer_agent_creation():
    """Test creating DataEngineerAgent."""
    agent = DataEngineerAgent()

    assert agent.name == "data_engineer"
    assert agent.description == "Data engineering agent for pipelines, SQL, and ETL"
    assert len(agent.pipelines) == 0


def test_data_engineer_agent_with_llm():
    """Test DataEngineerAgent with LLM provider."""
    mock_llm = Mock()
    agent = DataEngineerAgent(llm_provider=mock_llm)

    assert agent.llm == mock_llm


def test_data_engineer_agent_with_schema():
    """Test DataEngineerAgent with schema registry."""
    schema = {
        "users": {"id": "int", "name": "string", "age": "int"},
        "orders": {"id": "int", "user_id": "int", "amount": "float"}
    }

    agent = DataEngineerAgent(schema_registry=schema)

    assert agent.schema_registry == schema
    assert "users" in agent.schema_registry


# ===== Pipeline Building Tests =====

def test_build_simple_pipeline():
    """Test building a simple pipeline."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="users_raw",
        destination="users_clean"
    )

    assert pipeline.name == "users_raw_to_users_clean"
    assert pipeline.source == "users_raw"
    assert pipeline.destination == "users_clean"
    assert PipelineStage.EXTRACT in pipeline.stages
    assert PipelineStage.LOAD in pipeline.stages


def test_build_pipeline_with_transformations():
    """Test building pipeline with transformations."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="data_raw",
        destination="data_clean",
        transformations=["clean", "deduplicate", "aggregate"]
    )

    assert PipelineStage.CLEAN in pipeline.stages
    assert PipelineStage.AGGREGATE in pipeline.stages
    assert len(pipeline.transformations) > 0


def test_build_pipeline_with_schedule():
    """Test building pipeline with schedule."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="logs",
        destination="logs_processed",
        schedule="0 0 * * *"  # Daily at midnight
    )

    assert pipeline.schedule == "0 0 * * *"


def test_pipeline_stored_in_agent():
    """Test that pipeline is stored in agent."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="test_source",
        destination="test_dest",
        name="test_pipeline"
    )

    assert "test_pipeline" in agent.pipelines
    assert agent.get_pipeline("test_pipeline") == pipeline


# ===== SQL Generation Tests =====

def test_generate_sql_without_llm():
    """Test SQL generation without LLM (template-based)."""
    agent = DataEngineerAgent()

    sql = agent.generate_sql(
        "Select all users",
        tables=["users"]
    )

    assert "SELECT" in sql.upper()
    assert "users" in sql


def test_generate_sql_with_context():
    """Test SQL generation with context."""
    agent = DataEngineerAgent()

    sql = agent.generate_sql(
        "Get users",
        tables=["users"],
        context={"limit": 10}
    )

    assert "LIMIT 10" in sql


def test_generate_sql_with_llm():
    """Test SQL generation with LLM."""
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.text = "SELECT * FROM users WHERE age > 25"
    mock_llm.generate.return_value = mock_response

    agent = DataEngineerAgent(llm_provider=mock_llm)

    sql = agent.generate_sql(
        "Get users older than 25",
        tables=["users"]
    )

    assert "SELECT" in sql
    assert "users" in sql
    mock_llm.generate.assert_called_once()


def test_generate_sql_with_schema():
    """Test SQL generation uses schema information."""
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.text = "SELECT id, name FROM users"
    mock_llm.generate.return_value = mock_response

    schema = {
        "users": {"id": "int", "name": "string", "age": "int"}
    }

    agent = DataEngineerAgent(
        llm_provider=mock_llm,
        schema_registry=schema
    )

    sql = agent.generate_sql(
        "Get user names",
        tables=["users"]
    )

    # Verify schema was included in prompt
    call_args = mock_llm.generate.call_args
    prompt = call_args[0][0]
    assert "users" in prompt


# ===== Transformation Tests =====

def test_create_transformation():
    """Test creating a transformation."""
    agent = DataEngineerAgent()

    transformation = agent.create_transformation(
        description="Filter users by age",
        transformation_type="filter",
        input_tables=["users"],
        output_table="users_filtered"
    )

    assert transformation.type == TransformationType.FILTER
    assert transformation.config["input_tables"] == ["users"]
    assert transformation.config["output_table"] == "users_filtered"


def test_transformation_sql_generated():
    """Test that transformation includes SQL."""
    agent = DataEngineerAgent()

    transformation = agent.create_transformation(
        description="Get active users",
        transformation_type="filter",
        input_tables=["users"]
    )

    assert transformation.sql is not None
    assert len(transformation.sql) > 0


def test_transformation_type_detection():
    """Test automatic transformation type detection."""
    agent = DataEngineerAgent()

    # Filter transformation
    trans1 = agent.create_transformation(
        "Filter users where age > 25",
        input_tables=["users"]
    )
    assert trans1.type == TransformationType.FILTER

    # Aggregate transformation
    trans2 = agent.create_transformation(
        "Aggregate sales by region",
        input_tables=["sales"]
    )
    assert trans2.type == TransformationType.AGGREGATE

    # Join transformation
    trans3 = agent.create_transformation(
        "Join users with orders",
        input_tables=["users", "orders"]
    )
    assert trans3.type == TransformationType.JOIN


# ===== ETL Pipeline Tests =====

def test_build_etl_pipeline_simple():
    """Test building a simple ETL pipeline."""
    agent = DataEngineerAgent()

    pipeline = agent.build_etl_pipeline(
        source_config={
            "type": "table",
            "location": "raw_data",
            "format": "parquet"
        },
        transformations=[
            {"type": "filter", "condition": "status = 'active'"}
        ],
        destination_config={
            "type": "table",
            "location": "clean_data"
        }
    )

    assert pipeline.source == "raw_data"
    assert pipeline.destination == "clean_data"
    assert PipelineStage.FILTER in pipeline.stages
    assert len(pipeline.transformations) == 1


def test_build_etl_pipeline_complex():
    """Test building complex ETL pipeline."""
    agent = DataEngineerAgent()

    pipeline = agent.build_etl_pipeline(
        source_config={
            "type": "file",
            "location": "data/users.csv",
            "format": "csv"
        },
        transformations=[
            {"type": "clean"},
            {"type": "filter", "condition": "age >= 18"},
            {
                "type": "aggregate",
                "group_by": ["region"],
                "aggregations": {"user_count": "count"}
            }
        ],
        destination_config={
            "type": "table",
            "location": "user_stats"
        },
        name="user_analytics_pipeline"
    )

    assert pipeline.name == "user_analytics_pipeline"
    assert PipelineStage.CLEAN in pipeline.stages
    assert PipelineStage.FILTER in pipeline.stages
    assert PipelineStage.AGGREGATE in pipeline.stages
    assert len(pipeline.transformations) == 3


def test_etl_pipeline_metadata():
    """Test ETL pipeline stores metadata."""
    agent = DataEngineerAgent()

    source_config = {"type": "table", "location": "source"}
    dest_config = {"type": "table", "location": "dest"}

    pipeline = agent.build_etl_pipeline(
        source_config=source_config,
        transformations=[],
        destination_config=dest_config
    )

    assert "source_config" in pipeline.metadata
    assert "destination_config" in pipeline.metadata
    assert pipeline.metadata["source_config"] == source_config


# ===== Pipeline Execution Tests =====

def test_execute_pipeline_dry_run():
    """Test pipeline dry run execution."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="test_source",
        destination="test_dest",
        name="test_pipeline"
    )

    result = agent.execute_pipeline("test_pipeline", dry_run=True)

    assert result["status"] == "validated"
    assert "pipeline" in result
    assert "stages" in result


def test_execute_pipeline():
    """Test pipeline execution."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="test_source",
        destination="test_dest",
        name="exec_test"
    )

    result = agent.execute_pipeline("exec_test")

    assert result["pipeline"] == "exec_test"
    assert "stages" in result
    assert result["status"] in ["completed", "running"]


def test_execute_nonexistent_pipeline():
    """Test executing non-existent pipeline raises error."""
    agent = DataEngineerAgent()

    with pytest.raises(ValueError, match="not found"):
        agent.execute_pipeline("nonexistent")


# ===== Pipeline Management Tests =====

def test_list_pipelines():
    """Test listing pipelines."""
    agent = DataEngineerAgent()

    agent.build_pipeline("s1", "d1", name="pipeline1")
    agent.build_pipeline("s2", "d2", name="pipeline2")

    pipelines = agent.list_pipelines()

    assert len(pipelines) == 2
    assert "pipeline1" in pipelines
    assert "pipeline2" in pipelines


def test_get_pipeline():
    """Test getting specific pipeline."""
    agent = DataEngineerAgent()

    original = agent.build_pipeline("source", "dest", name="test")
    retrieved = agent.get_pipeline("test")

    assert retrieved == original
    assert retrieved.name == "test"


# ===== SQL Validation Tests =====

def test_validate_sql_valid():
    """Test SQL validation for valid SQL."""
    agent = DataEngineerAgent()

    result = agent.validate_sql("SELECT * FROM users WHERE age > 25")

    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_sql_warnings():
    """Test SQL validation warnings."""
    agent = DataEngineerAgent()

    result = agent.validate_sql("SELECT id, name")  # No FROM

    assert len(result["warnings"]) > 0


def test_validate_sql_dangerous():
    """Test SQL validation catches dangerous patterns."""
    agent = DataEngineerAgent()

    result = agent.validate_sql("DROP TABLE users")

    assert result["valid"] is False
    assert len(result["errors"]) > 0


# ===== Pipeline to Dict Tests =====

def test_pipeline_to_dict():
    """Test converting pipeline to dictionary."""
    agent = DataEngineerAgent()

    pipeline = agent.build_pipeline(
        source="test_source",
        destination="test_dest",
        transformations=["clean"],
        name="test_pipeline"
    )

    pipeline_dict = pipeline.to_dict()

    assert pipeline_dict["name"] == "test_pipeline"
    assert pipeline_dict["source"] == "test_source"
    assert pipeline_dict["destination"] == "test_dest"
    assert "stages" in pipeline_dict
    assert "transformations" in pipeline_dict
    assert isinstance(pipeline_dict["stages"], list)


# ===== Transformation Config Tests =====

def test_build_aggregate_sql():
    """Test building aggregate SQL."""
    agent = DataEngineerAgent()

    config = {
        "group_by": ["region", "category"],
        "aggregations": {
            "sales": "sum",
            "quantity": "count"
        }
    }

    sql = agent._build_aggregate_sql(config)

    assert "SUM(SALES)" in sql.upper()
    assert "COUNT(QUANTITY)" in sql.upper()
    assert "GROUP BY" in sql.upper()
    assert "region" in sql
    assert "category" in sql


def test_build_join_sql():
    """Test building join SQL."""
    agent = DataEngineerAgent()

    config = {
        "left_table": "users",
        "right_table": "orders",
        "join_type": "inner",
        "on": "users.id = orders.user_id"
    }

    sql = agent._build_join_sql(config)

    assert "INNER JOIN" in sql.upper()
    assert "orders" in sql
    assert "users.id = orders.user_id" in sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
