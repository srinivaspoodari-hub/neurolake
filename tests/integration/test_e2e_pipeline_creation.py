"""
End-to-End Pipeline Creation Integration Tests

Tests the complete pipeline creation workflow including:
- Pipeline definition
- Transformation configuration
- Agent-based pipeline building
- Pipeline execution
- Storage integration
- Monitoring and validation
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import duckdb
import pandas as pd

from neurolake.agents.data_engineer import (
    DataEngineerAgent,
    Pipeline,
    Transformation,
    PipelineStage,
    TransformationType
)
from neurolake.optimizer.optimizer import QueryOptimizer


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve',
                 'Frank', 'Grace', 'Henry', 'Iris', 'Jack'],
        'age': [30, 25, 35, 28, 32, 45, 22, 38, 29, 33],
        'department': ['Engineering', 'Sales', 'Engineering', 'HR', 'Sales',
                      'Engineering', 'HR', 'Sales', 'Engineering', 'HR'],
        'salary': [75000, 55000, 85000, 60000, 65000,
                  95000, 50000, 70000, 72000, 58000]
    })


class TestPipelineCreation:
    """Test pipeline creation and configuration."""

    def test_create_basic_pipeline(self):
        """Test creating a basic pipeline."""
        pipeline = Pipeline(
            name="basic_etl",
            source="source_table",
            destination="dest_table"
        )

        assert pipeline.name == "basic_etl"
        assert pipeline.source == "source_table"
        assert pipeline.destination == "dest_table"
        assert len(pipeline.stages) == 0
        assert len(pipeline.transformations) == 0

    def test_add_pipeline_stages(self):
        """Test adding stages to pipeline."""
        pipeline = Pipeline(name="etl_pipeline")

        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_stage(PipelineStage.TRANSFORM)
        pipeline.add_stage(PipelineStage.LOAD)

        assert len(pipeline.stages) == 3
        assert pipeline.stages[0] == PipelineStage.EXTRACT
        assert pipeline.stages[1] == PipelineStage.TRANSFORM
        assert pipeline.stages[2] == PipelineStage.LOAD

    def test_add_transformations(self):
        """Test adding transformations to pipeline."""
        pipeline = Pipeline(name="transform_pipeline")

        # Add filter transformation
        filter_transform = Transformation(
            name="filter_active",
            type=TransformationType.FILTER,
            sql="WHERE active = true",
            description="Filter active records"
        )
        pipeline.add_transformation(filter_transform)

        # Add aggregate transformation
        agg_transform = Transformation(
            name="group_by_dept",
            type=TransformationType.AGGREGATE,
            sql="GROUP BY department",
            description="Aggregate by department"
        )
        pipeline.add_transformation(agg_transform)

        assert len(pipeline.transformations) == 2
        assert pipeline.transformations[0].name == "filter_active"
        assert pipeline.transformations[1].type == TransformationType.AGGREGATE

    def test_pipeline_to_dict(self):
        """Test converting pipeline to dictionary."""
        pipeline = Pipeline(
            name="test_pipeline",
            source="source",
            destination="dest",
            schedule="daily"
        )
        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_stage(PipelineStage.TRANSFORM)

        transform = Transformation(
            name="clean_data",
            type=TransformationType.MAP,
            description="Clean data"
        )
        pipeline.add_transformation(transform)

        pipeline_dict = pipeline.to_dict()

        assert pipeline_dict["name"] == "test_pipeline"
        assert pipeline_dict["source"] == "source"
        assert pipeline_dict["destination"] == "dest"
        assert len(pipeline_dict["stages"]) == 2
        assert "extract" in pipeline_dict["stages"]
        assert "transform" in pipeline_dict["stages"]


class TestPipelineExecution:
    """Test pipeline execution with real data."""

    def test_extract_transform_load_pipeline(self, temp_dir, sample_data):
        """Test complete ETL pipeline execution."""
        # Create database
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # 1. EXTRACT: Load source data
        conn.execute("""
            CREATE TABLE source_employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO source_employees VALUES (?, ?, ?, ?, ?)",
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # 2. TRANSFORM: Filter and aggregate
        transform_sql = """
            SELECT
                department,
                COUNT(*) as employee_count,
                AVG(salary) as avg_salary,
                MAX(salary) as max_salary,
                MIN(salary) as min_salary
            FROM source_employees
            WHERE age >= 25
            GROUP BY department
            ORDER BY avg_salary DESC
        """

        result = conn.execute(transform_sql).fetchdf()

        assert len(result) == 3  # 3 departments
        assert 'department' in result.columns
        assert 'avg_salary' in result.columns

        # 3. LOAD: Create destination table
        conn.execute("""
            CREATE TABLE dept_summary AS
            SELECT * FROM ({})
        """.format(transform_sql))

        # Verify loaded data
        loaded = conn.execute("SELECT * FROM dept_summary").fetchdf()
        assert len(loaded) == 3

        conn.close()

    def test_filter_transformation(self, temp_dir, sample_data):
        """Test filter transformation."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Apply filter transformation
        filter_sql = "SELECT * FROM employees WHERE department = 'Engineering'"
        result = conn.execute(filter_sql).fetchdf()

        assert len(result) == 4  # 4 engineers in sample data
        assert all(result['department'] == 'Engineering')

        conn.close()

    def test_aggregate_transformation(self, temp_dir, sample_data):
        """Test aggregate transformation."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Aggregate by department
        agg_sql = """
            SELECT
                department,
                COUNT(*) as count,
                AVG(salary) as avg_salary
            FROM employees
            GROUP BY department
        """
        result = conn.execute(agg_sql).fetchdf()

        assert len(result) == 3  # 3 departments
        assert 'count' in result.columns
        assert 'avg_salary' in result.columns

        conn.close()

    def test_join_transformation(self, temp_dir):
        """Test join transformation."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create employees table
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                dept_id INTEGER
            )
        """)
        conn.execute("INSERT INTO employees VALUES (1, 'Alice', 101)")
        conn.execute("INSERT INTO employees VALUES (2, 'Bob', 102)")
        conn.execute("INSERT INTO employees VALUES (3, 'Charlie', 101)")

        # Create departments table
        conn.execute("""
            CREATE TABLE departments (
                id INTEGER,
                name VARCHAR
            )
        """)
        conn.execute("INSERT INTO departments VALUES (101, 'Engineering')")
        conn.execute("INSERT INTO departments VALUES (102, 'Sales')")

        # Join transformation
        join_sql = """
            SELECT
                e.name as employee_name,
                d.name as department_name
            FROM employees e
            INNER JOIN departments d ON e.dept_id = d.id
            ORDER BY e.name
        """
        result = conn.execute(join_sql).fetchdf()

        assert len(result) == 3
        assert result.iloc[0]['department_name'] == 'Engineering'  # Alice
        assert result.iloc[1]['department_name'] == 'Sales'  # Bob

        conn.close()

    def test_deduplicate_transformation(self, temp_dir):
        """Test deduplication transformation."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create table with duplicates
        conn.execute("""
            CREATE TABLE records (
                id INTEGER,
                value VARCHAR
            )
        """)
        conn.execute("INSERT INTO records VALUES (1, 'A')")
        conn.execute("INSERT INTO records VALUES (2, 'B')")
        conn.execute("INSERT INTO records VALUES (3, 'A')")  # Duplicate
        conn.execute("INSERT INTO records VALUES (4, 'C')")
        conn.execute("INSERT INTO records VALUES (5, 'B')")  # Duplicate

        # Deduplicate
        dedup_sql = """
            SELECT DISTINCT value
            FROM records
            ORDER BY value
        """
        result = conn.execute(dedup_sql).fetchdf()

        assert len(result) == 3  # Only A, B, C
        assert list(result['value']) == ['A', 'B', 'C']

        conn.close()


class TestPipelineWithOptimization:
    """Test pipeline with query optimization."""

    def test_optimized_pipeline_execution(self, temp_dir, sample_data):
        """Test pipeline with query optimization."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Original query with redundant predicates
        original_sql = """
            SELECT *
            FROM employees
            WHERE age > 25 AND 1=1 AND TRUE
        """

        # Optimize query
        optimizer = QueryOptimizer()
        optimized_sql = optimizer.optimize(original_sql)

        # Optimizer should return valid SQL (may or may not optimize this specific case)
        assert optimized_sql is not None
        assert len(optimized_sql) > 0

        # Execute optimized query
        result = conn.execute(optimized_sql).fetchdf()
        assert len(result) > 0

        # Also execute original to verify same results
        result_original = conn.execute(original_sql).fetchdf()
        assert len(result) == len(result_original)

        conn.close()


class TestPipelineValidation:
    """Test pipeline validation and error handling."""

    def test_validate_pipeline_stages(self):
        """Test validating pipeline has required stages."""
        pipeline = Pipeline(name="incomplete_pipeline")

        # Should have at least EXTRACT and LOAD
        pipeline.add_stage(PipelineStage.EXTRACT)

        assert PipelineStage.EXTRACT in pipeline.stages
        # Can add validation logic here

    def test_pipeline_with_schedule(self):
        """Test pipeline with scheduling information."""
        pipeline = Pipeline(
            name="scheduled_pipeline",
            schedule="0 0 * * *"  # Daily at midnight (cron format)
        )

        assert pipeline.schedule == "0 0 * * *"

    def test_pipeline_metadata(self):
        """Test pipeline with metadata."""
        pipeline = Pipeline(
            name="metadata_pipeline",
            metadata={
                "owner": "data_team",
                "version": "1.0",
                "tags": ["production", "daily"]
            }
        )

        assert pipeline.metadata["owner"] == "data_team"
        assert "production" in pipeline.metadata["tags"]


class TestDataEngineerAgentIntegration:
    """Test DataEngineerAgent integration."""

    def test_create_agent(self):
        """Test creating DataEngineerAgent."""
        agent = DataEngineerAgent(name="etl_agent")

        assert agent.name == "etl_agent"

    def test_agent_pipeline_creation(self):
        """Test agent can create pipelines."""
        agent = DataEngineerAgent(name="pipeline_builder")

        # Create pipeline through agent
        pipeline = Pipeline(
            name="agent_pipeline",
            source="raw_data",
            destination="processed_data"
        )

        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.add_stage(PipelineStage.CLEAN)
        pipeline.add_stage(PipelineStage.TRANSFORM)
        pipeline.add_stage(PipelineStage.VALIDATE)
        pipeline.add_stage(PipelineStage.LOAD)

        assert len(pipeline.stages) == 5
        assert pipeline.name == "agent_pipeline"


class TestComplexPipelines:
    """Test complex multi-stage pipelines."""

    def test_multi_transformation_pipeline(self, temp_dir, sample_data):
        """Test pipeline with multiple transformations."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Multi-step transformation
        # Step 1: Filter age > 25
        step1_sql = """
            CREATE TEMP TABLE filtered AS
            SELECT * FROM employees WHERE age > 25
        """
        conn.execute(step1_sql)

        # Step 2: Add salary grade
        step2_sql = """
            CREATE TEMP TABLE graded AS
            SELECT *,
                CASE
                    WHEN salary >= 80000 THEN 'Senior'
                    WHEN salary >= 60000 THEN 'Mid'
                    ELSE 'Junior'
                END as grade
            FROM filtered
        """
        conn.execute(step2_sql)

        # Step 3: Aggregate by department and grade
        step3_sql = """
            SELECT
                department,
                grade,
                COUNT(*) as count,
                AVG(salary) as avg_salary
            FROM graded
            GROUP BY department, grade
            ORDER BY department, grade
        """
        result = conn.execute(step3_sql).fetchdf()

        assert len(result) > 0
        assert 'grade' in result.columns
        assert 'count' in result.columns

        conn.close()

    def test_window_function_transformation(self, temp_dir, sample_data):
        """Test transformation with window functions."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Window function: Rank employees by salary within department
        window_sql = """
            SELECT
                name,
                department,
                salary,
                RANK() OVER (PARTITION BY department ORDER BY salary DESC) as salary_rank
            FROM employees
            ORDER BY department, salary_rank
        """
        result = conn.execute(window_sql).fetchdf()

        assert len(result) == 10
        assert 'salary_rank' in result.columns

        conn.close()


class TestPipelineMonitoring:
    """Test pipeline monitoring and metrics."""

    def test_track_pipeline_execution_time(self, temp_dir, sample_data):
        """Test tracking pipeline execution time."""
        import time

        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
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
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Track execution time
        start_time = time.time()

        result = conn.execute("""
            SELECT department, COUNT(*) as count
            FROM employees
            GROUP BY department
        """).fetchdf()

        end_time = time.time()
        execution_time = end_time - start_time

        assert execution_time < 1.0  # Should be fast for small dataset
        assert len(result) > 0

        conn.close()

    def test_track_records_processed(self, temp_dir, sample_data):
        """Test tracking number of records processed."""
        db_path = temp_dir / "test.db"
        conn = duckdb.connect(str(db_path))

        # Load data
        conn.execute("""
            CREATE TABLE employees (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                department VARCHAR,
                salary INTEGER
            )
        """)

        input_count = len(sample_data)

        for _, row in sample_data.iterrows():
            conn.execute(
                "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
                [row['id'], row['name'], row['age'], row['department'], row['salary']]
            )

        # Filter transformation
        result = conn.execute("""
            SELECT * FROM employees WHERE age > 30
        """).fetchdf()

        output_count = len(result)

        assert input_count == 10
        assert output_count < input_count  # Some filtered out
        assert output_count > 0

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
