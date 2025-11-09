"""
NeuroLake Query Engine

Main query engine for executing SQL queries with Spark integration.
"""

from typing import Optional, Dict, Any, List, Union
import re
import time
import uuid
import threading
from datetime import datetime
import pandas as pd

from neurolake.engine.exceptions import (
    QueryExecutionError,
    SQLValidationError,
    QueryTimeoutException,
    QueryCancelledException,
    BackendError,
    ResultConversionError,
)

try:
    from pyspark.sql import SparkSession, DataFrame as SparkDataFrame
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False
    SparkDataFrame = None


class NeuroLakeEngine:
    """Main query engine for NeuroLake."""
    
    def __init__(
        self,
        spark_session: Optional[Any] = None,
        default_timeout: int = 300,
        enable_validation: bool = True,
        track_history: bool = True,
        db_session: Optional[Any] = None,
        user_id: Optional[int] = None,
    ):
        self.default_timeout = default_timeout
        self.enable_validation = enable_validation
        self.track_history = track_history
        self.db_session = db_session
        self.user_id = user_id

        self._active_queries: Dict[str, threading.Thread] = {}
        self._cancelled_queries: set = set()
        self._query_history: List[Dict[str, Any]] = []

        if spark_session is None and SPARK_AVAILABLE:
            try:
                from neurolake.spark import get_spark_session
                self.spark = get_spark_session()
            except Exception:
                # Spark not available or Java not installed
                self.spark = None
        else:
            self.spark = spark_session

        self.backend = "spark" if self.spark is not None else "duckdb"
        self._duckdb_conn = None
    
    def execute_sql(
        self,
        sql: str,
        timeout: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        return_format: str = "dataframe",
        limit: Optional[int] = 10000,
        offset: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Union[pd.DataFrame, Dict[str, Any], Any]:
        """
        Execute SQL query with timeout and validation.

        Args:
            sql: SQL query to execute
            timeout: Query timeout in seconds (default: 300)
            params: Named parameters for parameterized queries
            return_format: Result format ("dataframe", "json", "spark")
            limit: Maximum number of rows to return (default: 10000, None for unlimited)
            offset: Number of rows to skip (for manual pagination)
            page: Page number (1-indexed, for automatic pagination with page_size)
            page_size: Rows per page (used with page parameter)

        Returns:
            Query results in requested format

        Examples:
            # Basic query
            df = engine.execute_sql("SELECT * FROM users")

            # With row limit
            df = engine.execute_sql("SELECT * FROM users", limit=100)

            # With pagination (page 2, 50 rows per page)
            df = engine.execute_sql("SELECT * FROM users", page=2, page_size=50)

            # With manual offset
            df = engine.execute_sql("SELECT * FROM users", limit=100, offset=200)
        """
        query_id = str(uuid.uuid4())
        timeout = timeout or self.default_timeout

        if self.enable_validation:
            self._validate_sql(sql)

        # Apply pagination/limits to SQL
        sql = self._apply_pagination(sql, limit, offset, page, page_size)

        table_names = self._extract_table_names(sql)
        start_time = time.time()

        try:
            result = self._execute_with_timeout(query_id, sql, timeout, params)
            execution_time = time.time() - start_time

            if self.track_history:
                self._add_to_history(
                    query_id, sql, table_names, execution_time, "success"
                )

            return self._convert_result(result, return_format)

        except Exception as e:
            execution_time = time.time() - start_time
            if self.track_history:
                self._add_to_history(
                    query_id, sql, table_names, execution_time, "failed", str(e)
                )
            raise
    
    def _validate_sql(self, sql: str):
        """Validate SQL syntax."""
        sql_stripped = sql.strip()
        
        if not sql_stripped:
            raise SQLValidationError("SQL query is empty")
        
        dangerous = [
            r"\bDROP\s+DATABASE\b",
            r"\bDROP\s+SCHEMA\b",
            r"\bTRUNCATE\s+TABLE\b",
        ]
        
        for pattern in dangerous:
            if re.search(pattern, sql_stripped, re.IGNORECASE):
                raise SQLValidationError(f"Dangerous operation: {pattern}")
        
        keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "WITH"]
        has_keyword = any(
            re.search(rf"\b{kw}\b", sql_stripped, re.IGNORECASE) for kw in keywords
        )
        
        if not has_keyword:
            raise SQLValidationError("Invalid SQL keyword")
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        tables = []
        
        patterns = [
            r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_\.]*)",
            r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_\.]*)",
            r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_\.]*)",
            r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_\.]*)",
        ]
        
        for pattern in patterns:
            tables.extend(re.findall(pattern, sql, re.IGNORECASE))
        
        return list(set(tables))
    
    def _substitute_parameters(
        self, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Substitute parameters in SQL query.

        Supports named parameters (:param_name) and validates parameters.
        For safety, parameters are properly escaped.

        Args:
            sql: SQL query with parameter placeholders
            params: Dictionary of parameter values

        Returns:
            SQL with substituted parameters

        Example:
            sql = "SELECT * FROM users WHERE id = :user_id AND age > :min_age"
            params = {"user_id": 123, "min_age": 18}
            # Returns: "SELECT * FROM users WHERE id = 123 AND age > 18"
        """
        if not params:
            return sql

        # Find all parameter placeholders
        import re
        placeholders = re.findall(r':(\w+)', sql)

        # Validate all required parameters are provided
        missing = set(placeholders) - set(params.keys())
        if missing:
            raise SQLValidationError(
                f"Missing required parameters: {', '.join(missing)}"
            )

        # Substitute parameters with proper escaping
        result_sql = sql
        for param_name, param_value in params.items():
            placeholder = f":{param_name}"

            # Type-based formatting for SQL safety
            if param_value is None:
                formatted_value = "NULL"
            elif isinstance(param_value, (int, float)):
                formatted_value = str(param_value)
            elif isinstance(param_value, bool):
                formatted_value = "TRUE" if param_value else "FALSE"
            elif isinstance(param_value, str):
                # Escape single quotes and wrap in quotes
                escaped_value = param_value.replace("'", "''")
                formatted_value = f"'{escaped_value}'"
            elif isinstance(param_value, (list, tuple)):
                # Convert to SQL list format
                formatted_items = []
                for item in param_value:
                    if isinstance(item, str):
                        escaped_item = item.replace("'", "''")
                        formatted_items.append(f"'{escaped_item}'")
                    else:
                        formatted_items.append(str(item))
                formatted_value = f"({', '.join(formatted_items)})"
            else:
                # Try to convert to string and escape
                escaped_value = str(param_value).replace("'", "''")
                formatted_value = f"'{escaped_value}'"

            result_sql = result_sql.replace(placeholder, formatted_value)

        return result_sql

    def _apply_pagination(
        self,
        sql: str,
        limit: Optional[int],
        offset: Optional[int],
        page: Optional[int],
        page_size: Optional[int],
    ) -> str:
        """
        Apply pagination and row limits to SQL query.

        Args:
            sql: Original SQL query
            limit: Maximum rows to return
            offset: Rows to skip
            page: Page number (1-indexed)
            page_size: Rows per page

        Returns:
            Modified SQL with LIMIT/OFFSET clauses
        """
        import re

        # Check if SQL already has LIMIT clause
        has_limit = bool(re.search(r'\bLIMIT\b', sql, re.IGNORECASE))

        # Calculate offset from page/page_size if provided
        if page is not None and page_size is not None:
            if page < 1:
                raise SQLValidationError("Page number must be >= 1")
            offset = (page - 1) * page_size
            limit = page_size

        # Don't add LIMIT if SQL already has one and no pagination params specified
        if has_limit and limit == 10000 and offset is None:
            return sql

        # Build LIMIT/OFFSET clause
        pagination_clause = ""
        if limit is not None:
            pagination_clause = f" LIMIT {limit}"
        if offset is not None:
            pagination_clause += f" OFFSET {offset}"

        # If SQL already has LIMIT, replace it
        if has_limit:
            # Remove existing LIMIT clause
            sql = re.sub(
                r'\bLIMIT\s+\d+(\s+OFFSET\s+\d+)?',
                '',
                sql,
                flags=re.IGNORECASE
            ).strip()

        # Add pagination clause
        return sql + pagination_clause

    def _execute_with_timeout(
        self, query_id: str, sql: str, timeout: int, params: Optional[Dict] = None
    ) -> Any:
        """Execute with timeout support."""
        result_container = {"result": None, "error": None}

        # Substitute parameters if provided
        if params:
            sql = self._substitute_parameters(sql, params)

        def execute_query():
            try:
                if query_id in self._cancelled_queries:
                    raise QueryCancelledException(f"Query {query_id} cancelled")

                if self.backend == "spark" and self.spark:
                    result_container["result"] = self.spark.sql(sql)
                else:
                    result_container["result"] = self._execute_duckdb(sql)
            except Exception as e:
                result_container["error"] = e

        thread = threading.Thread(target=execute_query)
        self._active_queries[query_id] = thread
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            self._cancelled_queries.add(query_id)
            raise QueryTimeoutException(f"Timeout after {timeout}s")

        self._active_queries.pop(query_id, None)

        if result_container["error"]:
            raise result_container["error"]

        return result_container["result"]
    
    def _execute_duckdb(self, sql: str) -> pd.DataFrame:
        """Execute using DuckDB fallback."""
        import duckdb
        if self._duckdb_conn is None:
            self._duckdb_conn = duckdb.connect(":memory:")
        return self._duckdb_conn.execute(sql).fetchdf()
    
    def _convert_result(
        self, result: Any, format: str
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Convert result to requested format."""
        if format == "spark":
            return result
        
        if hasattr(result, "toPandas"):
            pdf = result.toPandas()
        elif isinstance(result, pd.DataFrame):
            pdf = result
        else:
            pdf = pd.DataFrame(result)
        
        if format == "dataframe":
            return pdf
        elif format == "json":
            return {
                "columns": pdf.columns.tolist(),
                "data": pdf.to_dict(orient="records"),
                "row_count": len(pdf),
                "dtypes": {col: str(dtype) for col, dtype in pdf.dtypes.items()},
            }
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def cancel_query(self, query_id: str):
        """Cancel running query."""
        self._cancelled_queries.add(query_id)
    
    def _add_to_history(
        self, query_id, sql, tables, exec_time, status, error=None
    ):
        """Add to query history (in-memory and database)."""
        timestamp = datetime.now()

        # Add to in-memory history
        self._query_history.append({
            "query_id": query_id,
            "sql": sql,
            "table_names": tables,
            "execution_time": exec_time,
            "status": status,
            "error": error,
            "timestamp": timestamp.isoformat(),
        })

        # Also persist to database if db_session is available
        if self.db_session is not None:
            try:
                from sqlalchemy import text

                # Determine query type from SQL
                query_type = self._get_query_type(sql)

                # Calculate rows read (if result is available, we could track this better)
                # For now, set to NULL and let it be updated later

                insert_query = text("""
                    INSERT INTO query_history (
                        query_id, user_id, query_text, query_type, query_status,
                        tables_accessed, execution_time_ms, started_at, completed_at,
                        error_message, error_type
                    ) VALUES (
                        :query_id, :user_id, :query_text, :query_type, :query_status,
                        :tables_accessed, :execution_time_ms, :started_at, :completed_at,
                        :error_message, :error_type
                    )
                """)

                self.db_session.execute(insert_query, {
                    "query_id": query_id,
                    "user_id": self.user_id,
                    "query_text": sql,
                    "query_type": query_type,
                    "query_status": status,
                    "tables_accessed": tables,
                    "execution_time_ms": int(exec_time * 1000),  # Convert to milliseconds
                    "started_at": timestamp,
                    "completed_at": timestamp,
                    "error_message": error,
                    "error_type": type(error).__name__ if error else None,
                })

                self.db_session.commit()
            except Exception as e:
                # Don't fail the query if history logging fails
                import logging
                logging.warning(f"Failed to persist query history to database: {e}")
                if self.db_session:
                    self.db_session.rollback()

    def _get_query_type(self, sql: str) -> str:
        """Determine query type from SQL."""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('SELECT') or sql_upper.startswith('WITH'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        elif sql_upper.startswith('CREATE'):
            return 'CREATE'
        elif sql_upper.startswith('DROP'):
            return 'DROP'
        elif sql_upper.startswith('ALTER'):
            return 'ALTER'
        else:
            return 'OTHER'
    
    def get_query_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get query history."""
        if limit:
            return self._query_history[-limit:]
        return self._query_history
    
    def clear_history(self):
        """Clear history."""
        self._query_history.clear()
    
    def get_backend(self) -> str:
        """Get backend name."""
        return self.backend

    def explain(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        analyze: bool = False,
    ) -> pd.DataFrame:
        """
        Get query execution plan.

        Args:
            sql: SQL query to explain
            params: Query parameters
            analyze: If True, actually execute query and show real stats (EXPLAIN ANALYZE)

        Returns:
            DataFrame with query plan

        Example:
            plan = engine.explain("SELECT * FROM users WHERE id = :user_id", params={"user_id": 123})
            print(plan)
        """
        # Substitute parameters if provided
        if params:
            sql = self._substitute_parameters(sql, params)

        # Build EXPLAIN query
        if analyze:
            explain_sql = f"EXPLAIN ANALYZE {sql}"
        else:
            explain_sql = f"EXPLAIN {sql}"

        # Execute EXPLAIN without validation or history tracking
        if self.backend == "spark" and self.spark:
            result = self.spark.sql(explain_sql)
            return result.toPandas()
        else:
            return self._execute_duckdb(explain_sql)

    def get_query_plan(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get structured query plan information.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Dictionary with plan information

        Example:
            plan_info = engine.get_query_plan("SELECT * FROM users WHERE id = 123")
            print(f"Estimated cost: {plan_info['estimated_cost']}")
        """
        plan_df = self.explain(sql, params)

        # Parse plan into structured format
        plan_text = "\n".join(plan_df.iloc[:, 0].tolist())

        # Extract basic info (database-specific parsing)
        info = {
            "sql": sql,
            "backend": self.backend,
            "plan_text": plan_text,
            "plan_lines": plan_df.iloc[:, 0].tolist(),
            "timestamp": datetime.now().isoformat(),
        }

        # Try to extract cost estimate (DuckDB specific)
        import re
        cost_match = re.search(r'cost[:\s]+(\d+\.?\d*)', plan_text, re.IGNORECASE)
        if cost_match:
            info["estimated_cost"] = float(cost_match.group(1))

        # Try to extract row estimate
        rows_match = re.search(r'rows[:\s]+(\d+)', plan_text, re.IGNORECASE)
        if rows_match:
            info["estimated_rows"] = int(rows_match.group(1))

        return info

    def close(self):
        """Close connections."""
        if self._duckdb_conn:
            self._duckdb_conn.close()


__all__ = [
    "NeuroLakeEngine",
    "QueryCancelledException",
    "QueryTimeoutException",
    "SQLValidationError",
]
