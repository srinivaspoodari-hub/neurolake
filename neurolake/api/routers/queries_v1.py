"""
Queries API Router (v1)

SQL query execution endpoints with AI-powered optimization.
Protected with authentication and permission checks.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from neurolake.db import get_db_session
from neurolake.engine import NeuroLakeEngine
from neurolake.optimizer import QueryOptimizer
from neurolake.compliance import ComplianceEngine
from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    """SQL query execution request."""
    sql: str = Field(..., description="SQL query to execute", min_length=1)
    database: Optional[str] = Field(None, description="Target database")
    limit: Optional[int] = Field(1000, description="Result limit", ge=1, le=100000)
    timeout: Optional[int] = Field(60, description="Query timeout in seconds", ge=1, le=600)
    optimize: bool = Field(True, description="Enable AI query optimization")
    check_compliance: bool = Field(True, description="Check for compliance violations")


class QueryResponse(BaseModel):
    """SQL query execution response."""
    success: bool
    query_id: str
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time_ms: float = 0
    optimized: bool = False
    compliance_checked: bool = False
    compliance_warnings: List[str] = []
    error: Optional[str] = None


class ExplainResponse(BaseModel):
    """Query execution plan response."""
    query: str
    plan: str
    estimated_cost: Optional[float] = None
    optimizations: List[str] = []


@router.post("", response_model=QueryResponse, summary="Execute SQL Query")
async def execute_query(
    request: QueryRequest,
    current_user: User = Depends(PermissionChecker("query:execute")),
    db: Session = Depends(get_db_session)
) -> QueryResponse:
    """
    Execute a SQL query with optional optimization and compliance checking.

    **Required Permission:** `query:execute`

    Features:
    - AI-powered query optimization
    - Automatic compliance checking
    - Result limiting and pagination
    - Query timeout protection
    """
    import uuid
    import time

    query_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        sql = request.sql
        compliance_warnings = []

        # Compliance checking - check for PII in query
        if request.check_compliance:
            compliance_engine = ComplianceEngine()
            pii_results = compliance_engine.detect_pii(sql)
            if pii_results:
                compliance_warnings = [
                    f"Query contains potential PII: {result.entity_type.value} at position {result.start}"
                    for result in pii_results
                ]

        # Query optimization
        optimized = False
        if request.optimize:
            try:
                optimizer = QueryOptimizer()
                optimized_sql = optimizer.optimize(sql)
                if optimized_sql != sql:
                    sql = optimized_sql
                    optimized = True
            except Exception as e:
                logger.warning(f"Optimization failed: {e}, using original query")

        # Execute query with database session for history persistence
        engine = NeuroLakeEngine(
            db_session=db,
            user_id=current_user.id
        )

        # Execute and get result as JSON
        result_df = engine.execute_sql(
            sql,
            limit=request.limit,
            timeout=request.timeout,
            return_format="dataframe"
        )

        # Convert DataFrame to response format
        if result_df is not None and not result_df.empty:
            data = result_df.to_dict('records')
            columns = result_df.columns.tolist()
            row_count = len(result_df)
        else:
            data = []
            columns = []
            row_count = 0

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return QueryResponse(
            success=True,
            query_id=query_id,
            data=data,
            columns=columns,
            row_count=row_count,
            execution_time_ms=execution_time,
            optimized=optimized,
            compliance_checked=request.check_compliance,
            compliance_warnings=compliance_warnings
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Query execution error: {e}")

        return QueryResponse(
            success=False,
            query_id=query_id,
            execution_time_ms=execution_time,
            optimized=request.optimize,
            compliance_checked=request.check_compliance,
            error=str(e)
        )


@router.post("/explain", response_model=ExplainResponse, summary="Explain Query")
async def explain_query(
    request: QueryRequest,
    current_user: User = Depends(PermissionChecker("query:explain")),
    db: Session = Depends(get_db_session)
) -> ExplainResponse:
    """
    Get execution plan for a SQL query.

    **Required Permission:** `query:explain`

    Returns the query execution plan with cost estimates and
    suggested optimizations.
    """
    try:
        engine = NeuroLakeEngine()

        # Get query plan
        explain_sql = f"EXPLAIN {request.sql}"
        result_df = engine.execute_sql(explain_sql, return_format="dataframe")

        # Extract plan text
        plan_text = "\n".join(result_df.iloc[:, 0].tolist()) if result_df is not None else "No plan available"

        optimizations = []
        if request.optimize:
            try:
                optimizer = QueryOptimizer()
                # Get optimizer stats to suggest optimizations
                stats = optimizer.get_stats()

                # Apply optimization and check if changes were made
                optimized_sql = optimizer.optimize(request.sql)
                if optimized_sql != request.sql:
                    optimizations.append("Query can be optimized")
                    optimizations.append(f"Optimizer has {stats.get('enabled_rules', 0)} rules available")
            except Exception as e:
                logger.warning(f"Could not analyze optimizations: {e}")

        return ExplainResponse(
            query=request.sql,
            plan=plan_text,
            estimated_cost=None,  # Would require parsing EXPLAIN ANALYZE output
            optimizations=optimizations
        )

    except Exception as e:
        logger.error(f"Explain query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", summary="Query History")
async def get_query_history(
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get query execution history.

    **Required:** Authenticated user

    Returns paginated list of previously executed queries with
    execution statistics.
    """
    try:
        # Query the query_history table if it exists
        result = db.execute(
            """
            SELECT
                query_id,
                query_text,
                execution_time_ms,
                rows_read as row_count,
                query_status,
                created_at,
                error_message
            FROM query_history
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """,
            {"limit": limit, "offset": offset}
        )

        queries = [
            {
                "query_id": row[0],
                "sql": row[1],
                "execution_time_ms": row[2] or 0,
                "row_count": row[3] or 0,
                "status": row[4],
                "timestamp": row[5].isoformat() if row[5] else None,
                "error": row[6]
            }
            for row in result.fetchall()
        ]

        # Get total count
        total_result = db.execute("SELECT COUNT(*) FROM query_history")
        total = total_result.scalar() or 0

        return {
            "queries": queries,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.warning(f"Query history not available: {e}")
        # Return empty result if table doesn't exist
        return {
            "queries": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "Query history not available - table may not be created yet"
        }


@router.delete("/{query_id}/cancel", summary="Cancel Query")
async def cancel_query(
    query_id: str,
    current_user: User = Depends(PermissionChecker("query:cancel")),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Cancel a running query.

    **Required Permission:** `query:cancel`

    Args:
        query_id: Query ID to cancel

    Returns:
        Cancellation status
    """
    try:
        # Attempt to cancel query in database
        # For PostgreSQL, we can use pg_terminate_backend
        result = db.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE query LIKE :query_pattern
            AND state = 'active'
            """,
            {"query_pattern": f"%{query_id}%"}
        )

        terminated = result.scalar()

        return {
            "query_id": query_id,
            "status": "cancelled" if terminated else "not_found",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Query cancelled successfully" if terminated else "Query not found or already completed"
        }
    except Exception as e:
        logger.error(f"Failed to cancel query {query_id}: {e}")
        return {
            "query_id": query_id,
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
