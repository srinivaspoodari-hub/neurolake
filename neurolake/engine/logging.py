"""
Query Execution Logging and Metrics

Comprehensive logging for query execution with metrics collection.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
import json

# Configure logger
logger = logging.getLogger("neurolake.engine")


class QueryLogger:
    """Logger for query execution events."""
    
    def __init__(self, enable_metrics: bool = True):
        self.enable_metrics = enable_metrics
        self.metrics: Dict[str, Any] = {}
    
    def log_query_start(
        self,
        query_id: str,
        sql: str,
        user: Optional[str] = None,
        params: Optional[Dict] = None,
    ):
        """Log query start."""
        timestamp = datetime.now().isoformat()
        
        log_data = {
            "event": "query_start",
            "query_id": query_id,
            "sql": sql[:200],  # Truncate long SQL
            "user": user,
            "timestamp": timestamp,
        }
        
        logger.info(f"Query started: {query_id}", extra=log_data)
        
        if self.enable_metrics:
            self.metrics[query_id] = {
                "start_time": time.time(),
                "sql": sql,
                "user": user,
            }
    
    def log_query_completion(
        self,
        query_id: str,
        duration: float,
        row_count: Optional[int] = None,
        bytes_processed: Optional[int] = None,
    ):
        """Log query completion."""
        log_data = {
            "event": "query_complete",
            "query_id": query_id,
            "duration_seconds": duration,
            "row_count": row_count,
            "bytes_processed": bytes_processed,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(
            f"Query completed: {query_id} in {duration:.2f}s",
            extra=log_data
        )
        
        if self.enable_metrics and query_id in self.metrics:
            self.metrics[query_id].update({
                "duration": duration,
                "row_count": row_count,
                "bytes_processed": bytes_processed,
                "status": "success",
            })
    
    def log_query_error(
        self,
        query_id: str,
        error: Exception,
        stack_trace: str,
        duration: Optional[float] = None,
    ):
        """Log query error with stack trace."""
        log_data = {
            "event": "query_error",
            "query_id": query_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": stack_trace,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.error(
            f"Query failed: {query_id} - {str(error)}",
            extra=log_data,
            exc_info=True
        )
        
        if self.enable_metrics and query_id in self.metrics:
            self.metrics[query_id].update({
                "duration": duration,
                "status": "failed",
                "error": str(error),
                "error_type": type(error).__name__,
            })
    
    def get_metrics(self, query_id: Optional[str] = None) -> Dict[str, Any]:
        """Get collected metrics."""
        if query_id:
            return self.metrics.get(query_id, {})
        return self.metrics
    
    def clear_metrics(self):
        """Clear all metrics."""
        self.metrics.clear()


@contextmanager
def query_execution_context(
    query_id: str,
    sql: str,
    logger: QueryLogger,
    user: Optional[str] = None,
):
    """
    Context manager for query execution.
    
    Automatically logs start, completion, and errors.
    
    Example:
        with query_execution_context(query_id, sql, logger):
            result = execute_query(sql)
    """
    start_time = time.time()
    logger.log_query_start(query_id, sql, user)
    
    try:
        yield
        duration = time.time() - start_time
        logger.log_query_completion(query_id, duration)
    except Exception as e:
        duration = time.time() - start_time
        import traceback
        stack_trace = traceback.format_exc()
        logger.log_query_error(query_id, e, stack_trace, duration)
        raise


__all__ = [
    "QueryLogger",
    "query_execution_context",
]
