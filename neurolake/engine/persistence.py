"""
Query History Persistence

Save query execution history to PostgreSQL.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json


class QueryHistoryStore:
    """
    Store for persisting query history to PostgreSQL.
    
    Uses the query_history table created by Alembic migrations.
    """
    
    def __init__(self, engine=None):
        """
        Initialize store.
        
        Args:
            engine: SQLAlchemy engine (created from settings if None)
        """
        self.engine = engine
        self._init_engine()
    
    def _init_engine(self):
        """Initialize database engine."""
        if self.engine is None:
            try:
                from neurolake.config import get_settings
                from sqlalchemy import create_engine
                
                settings = get_settings()
                self.engine = create_engine(
                    settings.database.connection_string,
                    pool_size=5,
                    max_overflow=10,
                )
            except Exception:
                # Database not available
                self.engine = None
    
    def save_query(
        self,
        query_id: str,
        sql: str,
        user_id: Optional[int] = None,
        query_type: str = "SELECT",
        status: str = "pending",
        tables_accessed: Optional[List[str]] = None,
        execution_time_ms: Optional[int] = None,
        rows_read: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save query to database.
        
        Args:
            query_id: Unique query identifier
            sql: SQL query text
            user_id: User ID (optional)
            query_type: Query type (SELECT, INSERT, etc.)
            status: Query status (pending, running, success, failed)
            tables_accessed: List of table names
            execution_time_ms: Execution time in milliseconds
            rows_read: Number of rows read
            error_message: Error message if failed
            metadata: Additional metadata (JSON)
            
        Returns:
            True if saved successfully, False otherwise
        """
        if self.engine is None:
            return False
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO query_history (
                    query_id, query_text, user_id, query_type, query_status,
                    tables_accessed, execution_time_ms, rows_read,
                    error_message, metadata, started_at, created_at
                ) VALUES (
                    :query_id, :query_text, :user_id, :query_type, :status,
                    :tables_accessed, :execution_time_ms, :rows_read,
                    :error_message, :metadata, :started_at, :created_at
                )
            """)
            
            with self.engine.connect() as conn:
                conn.execute(query, {
                    "query_id": query_id,
                    "query_text": sql,
                    "user_id": user_id,
                    "query_type": query_type,
                    "status": status,
                    "tables_accessed": tables_accessed,
                    "execution_time_ms": execution_time_ms,
                    "rows_read": rows_read,
                    "error_message": error_message,
                    "metadata": json.dumps(metadata) if metadata else None,
                    "started_at": datetime.now(),
                    "created_at": datetime.now(),
                })
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Failed to save query: {e}")
            return False
    
    def update_query_status(
        self,
        query_id: str,
        status: str,
        execution_time_ms: Optional[int] = None,
        rows_read: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update query status."""
        if self.engine is None:
            return False
        
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE query_history 
                SET query_status = :status,
                    execution_time_ms = COALESCE(:execution_time_ms, execution_time_ms),
                    rows_read = COALESCE(:rows_read, rows_read),
                    error_message = :error_message,
                    completed_at = :completed_at
                WHERE query_id = :query_id
            """)
            
            with self.engine.connect() as conn:
                conn.execute(query, {
                    "query_id": query_id,
                    "status": status,
                    "execution_time_ms": execution_time_ms,
                    "rows_read": rows_read,
                    "error_message": error_message,
                    "completed_at": datetime.now(),
                })
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Failed to update query: {e}")
            return False
    
    def get_recent_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent queries from database."""
        if self.engine is None:
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT * FROM query_history
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"limit": limit})
                return [dict(row) for row in result]
            
        except Exception:
            return []


__all__ = ["QueryHistoryStore"]
