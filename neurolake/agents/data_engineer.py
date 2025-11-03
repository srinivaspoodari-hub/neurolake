"""
Data Engineer Agent

Specialized agent for data engineering tasks including pipeline building,
SQL generation, transformations, and ETL workflows.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from neurolake.agents.base import Agent, Action, ActionResult
from neurolake.agents.tools import Tool

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """ETL pipeline stages."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"
    CLEAN = "clean"
    AGGREGATE = "aggregate"
    JOIN = "join"
    FILTER = "filter"


class TransformationType(Enum):
    """Types of data transformations."""
    MAP = "map"  # Apply function to each row
    FILTER = "filter"  # Filter rows
    AGGREGATE = "aggregate"  # Group and aggregate
    JOIN = "join"  # Join datasets
    PIVOT = "pivot"  # Pivot table
    UNPIVOT = "unpivot"  # Unpivot table
    WINDOW = "window"  # Window functions
    UNION = "union"  # Union datasets
    DEDUPLICATE = "deduplicate"  # Remove duplicates


@dataclass
class Transformation:
    """A data transformation step."""
    name: str
    type: TransformationType
    config: Dict[str, Any] = field(default_factory=dict)
    sql: Optional[str] = None
    function: Optional[Callable] = None
    description: str = ""


@dataclass
class Pipeline:
    """A data pipeline."""
    name: str
    stages: List[PipelineStage] = field(default_factory=list)
    transformations: List[Transformation] = field(default_factory=list)
    source: Optional[str] = None
    destination: Optional[str] = None
    schedule: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_stage(self, stage: PipelineStage):
        """Add a pipeline stage."""
        self.stages.append(stage)

    def add_transformation(self, transformation: Transformation):
        """Add a transformation."""
        self.transformations.append(transformation)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "stages": [s.value for s in self.stages],
            "transformations": [
                {
                    "name": t.name,
                    "type": t.type.value,
                    "config": t.config,
                    "sql": t.sql,
                    "description": t.description
                }
                for t in self.transformations
            ],
            "source": self.source,
            "destination": self.destination,
            "schedule": self.schedule,
            "metadata": self.metadata
        }


class DataEngineerAgent(Agent):
    """
    Specialized agent for data engineering tasks.

    Example:
        agent = DataEngineerAgent(
            name="data_engineer",
            llm_provider=llm,
            storage_engine=storage
        )

        # Build a pipeline
        pipeline = agent.build_pipeline(
            source="users_raw",
            destination="users_clean",
            transformations=["clean", "deduplicate", "aggregate"]
        )

        # Generate SQL
        sql = agent.generate_sql(
            "Get monthly sales by region with totals"
        )

        # Create transformation
        transform = agent.create_transformation(
            "Calculate customer lifetime value",
            input_tables=["customers", "orders"]
        )
    """

    def __init__(
        self,
        name: str = "data_engineer",
        llm_provider: Optional[Any] = None,
        storage_engine: Optional[Any] = None,
        schema_registry: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize DataEngineerAgent.

        Args:
            name: Agent name
            llm_provider: LLM provider for SQL generation
            storage_engine: Storage engine for data access
            schema_registry: Schema information for tables
            **kwargs: Additional arguments for Agent
        """
        # Initialize base agent
        super().__init__(
            name=name,
            description="Data engineering agent for pipelines, SQL, and ETL",
            llm_provider=llm_provider,
            **kwargs
        )

        self.storage_engine = storage_engine
        self.schema_registry = schema_registry or {}
        self.pipelines: Dict[str, Pipeline] = {}

        logger.info(f"DataEngineerAgent '{name}' initialized")

    def build_pipeline(
        self,
        source: str,
        destination: str,
        transformations: Optional[List[str]] = None,
        schedule: Optional[str] = None,
        name: Optional[str] = None
    ) -> Pipeline:
        """
        Build a data pipeline.

        Args:
            source: Source table/dataset
            destination: Destination table/dataset
            transformations: List of transformation types
            schedule: Optional cron schedule
            name: Optional pipeline name

        Returns:
            Built Pipeline object
        """
        pipeline_name = name or f"{source}_to_{destination}"

        pipeline = Pipeline(
            name=pipeline_name,
            source=source,
            destination=destination,
            schedule=schedule
        )

        # Add standard ETL stages
        pipeline.add_stage(PipelineStage.EXTRACT)

        if transformations:
            for transform_type in transformations:
                # Add transformation stages
                if transform_type.lower() in ["clean", "cleanse"]:
                    pipeline.add_stage(PipelineStage.CLEAN)
                    pipeline.add_transformation(
                        self._create_clean_transformation(source)
                    )

                elif transform_type.lower() in ["dedupe", "deduplicate"]:
                    pipeline.add_transformation(
                        self._create_deduplicate_transformation(source)
                    )

                elif transform_type.lower() == "aggregate":
                    pipeline.add_stage(PipelineStage.AGGREGATE)

                elif transform_type.lower() == "join":
                    pipeline.add_stage(PipelineStage.JOIN)

                elif transform_type.lower() == "filter":
                    pipeline.add_stage(PipelineStage.FILTER)

                elif transform_type.lower() == "transform":
                    pipeline.add_stage(PipelineStage.TRANSFORM)

        # Always add validation and load
        pipeline.add_stage(PipelineStage.VALIDATE)
        pipeline.add_stage(PipelineStage.LOAD)

        # Store pipeline
        self.pipelines[pipeline_name] = pipeline

        logger.info(f"Built pipeline: {pipeline_name}")
        return pipeline

    def generate_sql(
        self,
        description: str,
        tables: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate SQL from natural language description.

        Args:
            description: Natural language description
            tables: Optional list of relevant tables
            context: Optional context (filters, limits, etc.)

        Returns:
            Generated SQL query
        """
        if not self.llm:
            # Fallback to template-based SQL generation
            return self._generate_sql_template(description, tables, context)

        # Use LLM to generate SQL
        prompt = self._build_sql_prompt(description, tables, context)
        response = self.llm.generate(prompt, temperature=0.3)

        # Extract SQL from response
        sql = self._extract_sql(response.text)

        logger.info(f"Generated SQL for: {description}")
        return sql

    def create_transformation(
        self,
        description: str,
        transformation_type: Optional[str] = None,
        input_tables: Optional[List[str]] = None,
        output_table: Optional[str] = None
    ) -> Transformation:
        """
        Create a data transformation.

        Args:
            description: Transformation description
            transformation_type: Type of transformation
            input_tables: Input tables
            output_table: Output table name

        Returns:
            Transformation object
        """
        # Detect transformation type if not provided
        if not transformation_type:
            transformation_type = self._detect_transformation_type(description)

        trans_type = TransformationType[transformation_type.upper()]

        # Generate SQL for transformation
        sql = self.generate_sql(
            description,
            tables=input_tables
        )

        transformation = Transformation(
            name=description[:50],  # Use first 50 chars as name
            type=trans_type,
            config={
                "input_tables": input_tables or [],
                "output_table": output_table
            },
            sql=sql,
            description=description
        )

        logger.info(f"Created transformation: {transformation.name}")
        return transformation

    def build_etl_pipeline(
        self,
        source_config: Dict[str, Any],
        transformations: List[Dict[str, Any]],
        destination_config: Dict[str, Any],
        name: Optional[str] = None
    ) -> Pipeline:
        """
        Build a complete ETL pipeline.

        Args:
            source_config: Source configuration
                {
                    "type": "table|file|api",
                    "location": "path/table_name",
                    "format": "csv|json|parquet|..."
                }
            transformations: List of transformation configs
                [
                    {
                        "type": "filter",
                        "condition": "age > 25"
                    },
                    {
                        "type": "aggregate",
                        "group_by": ["region"],
                        "aggregations": {"sales": "sum"}
                    }
                ]
            destination_config: Destination configuration
            name: Pipeline name

        Returns:
            ETL Pipeline
        """
        pipeline_name = name or f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        pipeline = Pipeline(
            name=pipeline_name,
            source=source_config.get("location"),
            destination=destination_config.get("location")
        )

        # Extract stage
        pipeline.add_stage(PipelineStage.EXTRACT)
        pipeline.metadata["source_config"] = source_config

        # Transform stages
        for trans_config in transformations:
            trans_type = trans_config.get("type", "transform")

            if trans_type == "filter":
                pipeline.add_stage(PipelineStage.FILTER)
                transformation = Transformation(
                    name=f"filter_{trans_config.get('condition', '')}",
                    type=TransformationType.FILTER,
                    config=trans_config,
                    sql=f"WHERE {trans_config.get('condition', 'TRUE')}"
                )
                pipeline.add_transformation(transformation)

            elif trans_type == "aggregate":
                pipeline.add_stage(PipelineStage.AGGREGATE)
                transformation = Transformation(
                    name="aggregate",
                    type=TransformationType.AGGREGATE,
                    config=trans_config,
                    sql=self._build_aggregate_sql(trans_config)
                )
                pipeline.add_transformation(transformation)

            elif trans_type == "join":
                pipeline.add_stage(PipelineStage.JOIN)
                transformation = Transformation(
                    name="join",
                    type=TransformationType.JOIN,
                    config=trans_config,
                    sql=self._build_join_sql(trans_config)
                )
                pipeline.add_transformation(transformation)

            elif trans_type == "clean":
                pipeline.add_stage(PipelineStage.CLEAN)
                transformation = Transformation(
                    name="clean_data",
                    type=TransformationType.MAP,
                    config=trans_config
                )
                pipeline.add_transformation(transformation)

            else:
                # Generic transformation
                pipeline.add_stage(PipelineStage.TRANSFORM)
                transformation = Transformation(
                    name=trans_type,
                    type=TransformationType.MAP,
                    config=trans_config
                )
                pipeline.add_transformation(transformation)

        # Validate stage
        pipeline.add_stage(PipelineStage.VALIDATE)

        # Load stage
        pipeline.add_stage(PipelineStage.LOAD)
        pipeline.metadata["destination_config"] = destination_config

        # Store pipeline
        self.pipelines[pipeline_name] = pipeline

        logger.info(f"Built ETL pipeline: {pipeline_name}")
        return pipeline

    def execute_pipeline(
        self,
        pipeline_name: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a pipeline.

        Args:
            pipeline_name: Pipeline name
            dry_run: If True, validate but don't execute

        Returns:
            Execution results
        """
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            raise ValueError(f"Pipeline '{pipeline_name}' not found")

        if dry_run:
            return {
                "status": "validated",
                "pipeline": pipeline.to_dict(),
                "stages": [s.value for s in pipeline.stages]
            }

        # Execute pipeline stages
        results = {
            "pipeline": pipeline_name,
            "stages": [],
            "status": "running"
        }

        try:
            for i, stage in enumerate(pipeline.stages):
                stage_result = self._execute_stage(stage, pipeline, i)
                results["stages"].append(stage_result)

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Pipeline execution failed: {e}")

        return results

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get a pipeline by name."""
        return self.pipelines.get(name)

    def list_pipelines(self) -> List[str]:
        """List all pipeline names."""
        return list(self.pipelines.keys())

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL syntax and semantics.

        Args:
            sql: SQL query to validate

        Returns:
            Validation results
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Basic syntax checks
        sql_lower = sql.lower().strip()

        # Check for SELECT without FROM
        if "select" in sql_lower and "from" not in sql_lower:
            validation["warnings"].append("SELECT without FROM clause")

        # Check for common SQL injection patterns
        dangerous_patterns = ["drop table", "delete from", "--", "/*"]
        for pattern in dangerous_patterns:
            if pattern in sql_lower:
                validation["errors"].append(f"Potentially dangerous pattern: {pattern}")
                validation["valid"] = False

        return validation

    # Private helper methods

    def _create_clean_transformation(self, table: str) -> Transformation:
        """Create data cleaning transformation."""
        return Transformation(
            name="clean_data",
            type=TransformationType.MAP,
            config={"table": table},
            sql=f"""
                SELECT
                    TRIM(column_name) as column_name,
                    COALESCE(other_column, 'default') as other_column
                FROM {table}
                WHERE column_name IS NOT NULL
            """.strip(),
            description="Clean and normalize data"
        )

    def _create_deduplicate_transformation(self, table: str) -> Transformation:
        """Create deduplication transformation."""
        return Transformation(
            name="deduplicate",
            type=TransformationType.DEDUPLICATE,
            config={"table": table},
            sql=f"""
                SELECT DISTINCT *
                FROM {table}
            """.strip(),
            description="Remove duplicate records"
        )

    def _generate_sql_template(
        self,
        description: str,
        tables: Optional[List[str]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate SQL using templates (fallback)."""
        desc_lower = description.lower()

        # Simple pattern matching
        if "select" in desc_lower or "get" in desc_lower or "show" in desc_lower:
            table = tables[0] if tables else "table_name"
            sql = f"SELECT * FROM {table}"

            if "where" in desc_lower or context and context.get("filter"):
                sql += " WHERE 1=1"

            if context and context.get("limit"):
                sql += f" LIMIT {context['limit']}"

            return sql

        return "SELECT 1 -- Could not generate SQL from description"

    def _build_sql_prompt(
        self,
        description: str,
        tables: Optional[List[str]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for SQL generation."""
        prompt = f"""You are a SQL expert. Generate a SQL query for the following request:

Request: {description}

"""
        if tables:
            prompt += f"Available tables: {', '.join(tables)}\n\n"

        if self.schema_registry and tables:
            prompt += "Table schemas:\n"
            for table in tables:
                if table in self.schema_registry:
                    prompt += f"- {table}: {self.schema_registry[table]}\n"

        if context:
            prompt += f"\nAdditional context: {context}\n"

        prompt += """
Generate a SQL query that fulfills this request.
Return only the SQL query without explanation.
"""
        return prompt

    def _extract_sql(self, text: str) -> str:
        """Extract SQL from LLM response."""
        import re

        # Look for SQL code blocks
        sql_match = re.search(r'```sql\n(.*?)\n```', text, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()

        # Look for SELECT statements
        select_match = re.search(r'(SELECT.*?;?)\s*$', text, re.DOTALL | re.IGNORECASE)
        if select_match:
            return select_match.group(1).strip()

        # Return as-is if nothing found
        return text.strip()

    def _detect_transformation_type(self, description: str) -> str:
        """Detect transformation type from description."""
        desc_lower = description.lower()

        if "filter" in desc_lower or "where" in desc_lower:
            return "FILTER"
        elif "aggregate" in desc_lower or "group" in desc_lower or "sum" in desc_lower:
            return "AGGREGATE"
        elif "join" in desc_lower or "merge" in desc_lower:
            return "JOIN"
        elif "pivot" in desc_lower:
            return "PIVOT"
        elif "union" in desc_lower or "combine" in desc_lower:
            return "UNION"
        elif "dedupe" in desc_lower or "duplicate" in desc_lower:
            return "DEDUPLICATE"
        else:
            return "MAP"

    def _build_aggregate_sql(self, config: Dict[str, Any]) -> str:
        """Build SQL for aggregation."""
        group_by = config.get("group_by", [])
        aggregations = config.get("aggregations", {})

        agg_parts = []
        for col, func in aggregations.items():
            agg_parts.append(f"{func.upper()}({col}) as {col}_{func}")

        select_parts = group_by + agg_parts

        sql = f"SELECT {', '.join(select_parts)}"
        if group_by:
            sql += f" GROUP BY {', '.join(group_by)}"

        return sql

    def _build_join_sql(self, config: Dict[str, Any]) -> str:
        """Build SQL for join."""
        left_table = config.get("left_table", "table1")
        right_table = config.get("right_table", "table2")
        join_type = config.get("join_type", "INNER").upper()
        on_condition = config.get("on", "table1.id = table2.id")

        return f"{join_type} JOIN {right_table} ON {on_condition}"

    def _execute_stage(
        self,
        stage: PipelineStage,
        pipeline: Pipeline,
        stage_index: int
    ) -> Dict[str, Any]:
        """Execute a single pipeline stage."""
        stage_result = {
            "stage": stage.value,
            "index": stage_index,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }

        # Simulate stage execution
        if self.storage_engine:
            # Use actual storage engine
            pass
        else:
            # Simulate
            logger.info(f"Executing stage: {stage.value}")

        return stage_result


__all__ = [
    "DataEngineerAgent",
    "Pipeline",
    "Transformation",
    "PipelineStage",
    "TransformationType",
]
