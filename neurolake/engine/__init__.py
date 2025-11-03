"""
NeuroLake Query Engine

SQL query execution engine with:
- Spark integration
- SQL validation
- Query timeout and cancellation
- Result format conversion
- Query history tracking
- Error handling and logging
- Metrics collection
- PostgreSQL persistence

Example:
    from neurolake.engine import NeuroLakeEngine

    engine = NeuroLakeEngine()
    result = engine.execute_sql("SELECT * FROM table LIMIT 10")
    df = result  # pandas DataFrame by default

    # Or get JSON
    result_json = engine.execute_sql(
        "SELECT * FROM table",
        return_format="json"
    )
"""

from neurolake.engine.query import NeuroLakeEngine
from neurolake.engine.exceptions import (
    QueryExecutionError,
    SQLValidationError,
    QueryTimeoutException,
    QueryCancelledException,
    BackendError,
    ResultConversionError,
)
from neurolake.engine.logging import QueryLogger, query_execution_context
from neurolake.engine.persistence import QueryHistoryStore
from neurolake.engine.dashboard import QueryDashboard
from neurolake.engine.templates import (
    QueryTemplate,
    PreparedStatement,
    TemplateRegistry,
    get_template_registry,
)
from neurolake.engine.plan_visualization import QueryPlanVisualizer

__all__ = [
    "NeuroLakeEngine",
    "QueryExecutionError",
    "SQLValidationError",
    "QueryTimeoutException",
    "QueryCancelledException",
    "BackendError",
    "ResultConversionError",
    "QueryLogger",
    "query_execution_context",
    "QueryHistoryStore",
    "QueryDashboard",
    "QueryTemplate",
    "PreparedStatement",
    "TemplateRegistry",
    "get_template_registry",
    "QueryPlanVisualizer",
]
