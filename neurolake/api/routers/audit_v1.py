"""
Audit API Router (v1)

Audit log viewing and management endpoints.
View system audit trail for compliance and security monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from neurolake.db import get_db_session
from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models
class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    resource_name: Optional[str]
    status: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    changes: Optional[Dict[str, Any]]
    error_message: Optional[str]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]


class AuditLogListResponse(BaseModel):
    """Audit log list response."""
    logs: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""
    total_events: int
    by_action: Dict[str, int]
    by_resource: Dict[str, int]
    by_status: Dict[str, int]
    by_user: Dict[str, int]
    time_range: Dict[str, str]


# Endpoints

@router.get("", response_model=AuditLogListResponse, summary="Get Audit Logs")
async def get_audit_logs(
    user_id: Optional[int] = QueryParam(None, description="Filter by user ID"),
    action: Optional[str] = QueryParam(None, description="Filter by action"),
    resource_type: Optional[str] = QueryParam(None, description="Filter by resource type"),
    resource_id: Optional[str] = QueryParam(None, description="Filter by resource ID"),
    status: Optional[str] = QueryParam(None, description="Filter by status (success/failure)"),
    start_date: Optional[datetime] = QueryParam(None, description="Start date for time range"),
    end_date: Optional[datetime] = QueryParam(None, description="End date for time range"),
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> AuditLogListResponse:
    """
    Get audit logs with optional filtering.

    **Required:** Authenticated user (non-admins can only see their own logs)

    Returns paginated audit log entries. Admins can see all logs,
    regular users can only see their own activities.
    """
    try:
        # Build query with filters
        where_clauses = []
        params = {"limit": limit, "offset": offset}

        # Non-admins can only see their own logs
        if not current_user.is_superuser:
            where_clauses.append("al.user_id = :current_user_id")
            params["current_user_id"] = current_user.id

        # Apply filters
        if user_id is not None:
            where_clauses.append("al.user_id = :user_id")
            params["user_id"] = user_id

        if action:
            where_clauses.append("al.action = :action")
            params["action"] = action

        if resource_type:
            where_clauses.append("al.resource_type = :resource_type")
            params["resource_type"] = resource_type

        if resource_id:
            where_clauses.append("al.resource_id = :resource_id")
            params["resource_id"] = resource_id

        if status:
            where_clauses.append("al.status = :status")
            params["status"] = status

        if start_date:
            where_clauses.append("al.timestamp >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_clauses.append("al.timestamp <= :end_date")
            params["end_date"] = end_date

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Get audit logs
        query = text(f"""
            SELECT
                al.id, al.user_id, u.username, al.action, al.resource_type,
                al.resource_id, al.resource_name, al.status, al.ip_address,
                al.user_agent, al.changes, al.error_message, al.timestamp, al.metadata
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            {where_clause}
            ORDER BY al.timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        result = db.execute(query, params)

        logs = [
            AuditLogEntry(
                id=row[0],
                user_id=row[1],
                username=row[2],
                action=row[3],
                resource_type=row[4],
                resource_id=row[5],
                resource_name=row[6],
                status=row[7],
                ip_address=row[8],
                user_agent=row[9],
                changes=row[10],
                error_message=row[11],
                timestamp=row[12],
                metadata=row[13]
            )
            for row in result.fetchall()
        ]

        # Get total count
        count_query = text(f"""
            SELECT COUNT(*)
            FROM audit_logs al
            {where_clause}
        """)
        total_result = db.execute(count_query, {k: v for k, v in params.items() if k not in ["limit", "offset"]})
        total = total_result.scalar() or 0

        return AuditLogListResponse(
            logs=logs,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=AuditLogListResponse, summary="Get User Audit Trail")
async def get_user_audit_trail(
    user_id: int,
    action: Optional[str] = QueryParam(None),
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> AuditLogListResponse:
    """
    Get complete audit trail for a specific user.

    **Required:** Authenticated user (can view own trail, admins can view any)

    Returns all actions performed by the specified user.
    """
    try:
        # Check permissions
        if not current_user.is_superuser and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own audit trail"
            )

        # Build query
        where_clauses = ["al.user_id = :user_id"]
        params = {"user_id": user_id, "limit": limit, "offset": offset}

        if action:
            where_clauses.append("al.action = :action")
            params["action"] = action

        where_clause = "WHERE " + " AND ".join(where_clauses)

        query = text(f"""
            SELECT
                al.id, al.user_id, u.username, al.action, al.resource_type,
                al.resource_id, al.resource_name, al.status, al.ip_address,
                al.user_agent, al.changes, al.error_message, al.timestamp, al.metadata
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            {where_clause}
            ORDER BY al.timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        result = db.execute(query, params)

        logs = [
            AuditLogEntry(
                id=row[0],
                user_id=row[1],
                username=row[2],
                action=row[3],
                resource_type=row[4],
                resource_id=row[5],
                resource_name=row[6],
                status=row[7],
                ip_address=row[8],
                user_agent=row[9],
                changes=row[10],
                error_message=row[11],
                timestamp=row[12],
                metadata=row[13]
            )
            for row in result.fetchall()
        ]

        # Get total count
        count_query = text(f"""
            SELECT COUNT(*)
            FROM audit_logs al
            {where_clause}
        """)
        total_result = db.execute(count_query, {k: v for k, v in params.items() if k not in ["limit", "offset"]})
        total = total_result.scalar() or 0

        return AuditLogListResponse(
            logs=logs,
            total=total,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user audit trail for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=AuditStatsResponse, summary="Get Audit Statistics")
async def get_audit_stats(
    start_date: Optional[datetime] = QueryParam(None),
    end_date: Optional[datetime] = QueryParam(None),
    current_user: User = Depends(PermissionChecker("admin:system")),
    db: Session = Depends(get_db_session)
) -> AuditStatsResponse:
    """
    Get audit log statistics.

    **Required Permission:** `admin:system`

    Returns aggregated statistics about audit events.
    """
    try:
        # Default time range: last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        where_clause = "WHERE timestamp BETWEEN :start_date AND :end_date"
        params = {"start_date": start_date, "end_date": end_date}

        # Total events
        total_result = db.execute(
            text(f"SELECT COUNT(*) FROM audit_logs {where_clause}"),
            params
        )
        total_events = total_result.scalar() or 0

        # By action
        action_result = db.execute(
            text(f"""
                SELECT action, COUNT(*) as count
                FROM audit_logs
                {where_clause}
                GROUP BY action
                ORDER BY count DESC
            """),
            params
        )
        by_action = {row[0]: row[1] for row in action_result.fetchall()}

        # By resource type
        resource_result = db.execute(
            text(f"""
                SELECT resource_type, COUNT(*) as count
                FROM audit_logs
                {where_clause}
                GROUP BY resource_type
                ORDER BY count DESC
            """),
            params
        )
        by_resource = {row[0]: row[1] for row in resource_result.fetchall()}

        # By status
        status_result = db.execute(
            text(f"""
                SELECT status, COUNT(*) as count
                FROM audit_logs
                {where_clause}
                GROUP BY status
            """),
            params
        )
        by_status = {row[0]: row[1] for row in status_result.fetchall()}

        # By user (top 10)
        user_result = db.execute(
            text(f"""
                SELECT u.username, COUNT(*) as count
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                {where_clause}
                GROUP BY u.username
                ORDER BY count DESC
                LIMIT 10
            """),
            params
        )
        by_user = {row[0] or 'Unknown': row[1] for row in user_result.fetchall()}

        return AuditStatsResponse(
            total_events=total_events,
            by_action=by_action,
            by_resource=by_resource,
            by_status=by_status,
            by_user=by_user,
            time_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{audit_id}", response_model=AuditLogEntry, summary="Get Audit Log Entry")
async def get_audit_log_entry(
    audit_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> AuditLogEntry:
    """
    Get a specific audit log entry by ID.

    **Required:** Authenticated user (can view own entries, admins can view any)

    Returns detailed information about a specific audit event.
    """
    try:
        query = text("""
            SELECT
                al.id, al.user_id, u.username, al.action, al.resource_type,
                al.resource_id, al.resource_name, al.status, al.ip_address,
                al.user_agent, al.changes, al.error_message, al.timestamp, al.metadata
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.id = :audit_id
        """)

        result = db.execute(query, {"audit_id": audit_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Audit log entry not found")

        # Check permissions
        if not current_user.is_superuser and row[1] != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own audit entries"
            )

        return AuditLogEntry(
            id=row[0],
            user_id=row[1],
            username=row[2],
            action=row[3],
            resource_type=row[4],
            resource_id=row[5],
            resource_name=row[6],
            status=row[7],
            ip_address=row[8],
            user_agent=row[9],
            changes=row[10],
            error_message=row[11],
            timestamp=row[12],
            metadata=row[13]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit log entry {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
