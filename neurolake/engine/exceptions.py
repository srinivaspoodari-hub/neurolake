"""
NeuroLake Engine Exceptions

Custom exception classes for query engine errors.
"""

from typing import Optional, Dict, Any
import traceback


class QueryExecutionError(Exception):
    """
    Base exception for query execution errors.
    
    Attributes:
        message: Error message
        query_id: Query identifier
        sql: SQL query that caused error
        original_error: Original exception
        stack_trace: Full stack trace
        context: Additional error context
    """
    
    def __init__(
        self,
        message: str,
        query_id: Optional[str] = None,
        sql: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.query_id = query_id
        self.sql = sql
        self.original_error = original_error
        self.context = context or {}
        self.stack_trace = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "query_id": self.query_id,
            "sql": self.sql,
            "original_error": str(self.original_error) if self.original_error else None,
            "stack_trace": self.stack_trace,
            "context": self.context,
        }


class SQLValidationError(QueryExecutionError):
    """SQL validation failed."""
    pass


class QueryTimeoutException(QueryExecutionError):
    """Query exceeded timeout."""
    pass


class QueryCancelledException(QueryExecutionError):
    """Query was cancelled."""
    pass


class BackendError(QueryExecutionError):
    """Backend execution error (Spark/DuckDB)."""
    pass


class ResultConversionError(QueryExecutionError):
    """Error converting query results."""
    pass


__all__ = [
    "QueryExecutionError",
    "SQLValidationError",
    "QueryTimeoutException",
    "QueryCancelledException",
    "BackendError",
    "ResultConversionError",
]
