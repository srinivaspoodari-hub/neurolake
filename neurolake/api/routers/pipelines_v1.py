"""
Pipelines API Router (v1)

Data pipeline management endpoints.
Protected with authentication and permission checks.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from neurolake.db import get_db_session
from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models
class PipelineCreate(BaseModel):
    """Pipeline creation request."""
    pipeline_name: str = Field(..., min_length=1, max_length=255)
    pipeline_type: str = Field(..., pattern="^(ETL|ELT|streaming|batch)$")
    description: Optional[str] = None
    schedule_cron: Optional[str] = Field(None, description="Cron expression for scheduling")
    source_config: Dict[str, Any] = Field(..., description="Source connection configuration")
    destination_config: Dict[str, Any] = Field(..., description="Destination configuration")
    transformation_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class PipelineUpdate(BaseModel):
    """Pipeline update request."""
    description: Optional[str] = None
    is_active: Optional[bool] = None
    schedule_cron: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    destination_config: Optional[Dict[str, Any]] = None
    transformation_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class PipelineResponse(BaseModel):
    """Pipeline response."""
    id: int
    pipeline_name: str
    pipeline_type: str
    description: Optional[str]
    owner_user_id: Optional[int]
    is_active: bool
    schedule_cron: Optional[str]
    status: str
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_duration_ms: Optional[int]
    last_run_rows_processed: Optional[int]
    total_runs: int
    successful_runs: int
    failed_runs: int
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[str]]


class PipelineRunRequest(BaseModel):
    """Pipeline execution request."""
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Runtime parameters")


class PipelineRunResponse(BaseModel):
    """Pipeline execution response."""
    run_id: str
    pipeline_id: int
    status: str
    started_at: datetime
    message: str


# Endpoints

@router.get("", response_model=List[PipelineResponse], summary="List Pipelines")
async def list_pipelines(
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    pipeline_type: Optional[str] = QueryParam(None),
    status: Optional[str] = QueryParam(None),
    tag: Optional[str] = QueryParam(None),
    current_user: User = Depends(PermissionChecker("pipeline:read")),
    db: Session = Depends(get_db_session)
) -> List[PipelineResponse]:
    """
    Get all pipelines with optional filtering.

    **Required Permission:** `pipeline:read`
    """
    try:
        query = """
            SELECT
                id, pipeline_name, pipeline_type, description, owner_user_id,
                is_active, schedule_cron, status, last_run_at, last_run_status,
                last_run_duration_ms, last_run_rows_processed,
                total_runs, successful_runs, failed_runs,
                created_at, updated_at, tags
            FROM pipelines
            WHERE 1=1
        """
        params = {"limit": limit, "offset": offset}

        if pipeline_type:
            query += " AND pipeline_type = :pipeline_type"
            params["pipeline_type"] = pipeline_type

        if status:
            query += " AND status = :status"
            params["status"] = status

        if tag:
            query += " AND :tag = ANY(tags)"
            params["tag"] = tag

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        result = db.execute(text(query), params)
        pipelines = [
            PipelineResponse(
                id=row[0],
                pipeline_name=row[1],
                pipeline_type=row[2],
                description=row[3],
                owner_user_id=row[4],
                is_active=row[5],
                schedule_cron=row[6],
                status=row[7],
                last_run_at=row[8],
                last_run_status=row[9],
                last_run_duration_ms=row[10],
                last_run_rows_processed=row[11],
                total_runs=row[12],
                successful_runs=row[13],
                failed_runs=row[14],
                created_at=row[15],
                updated_at=row[16],
                tags=row[17] or []
            )
            for row in result.fetchall()
        ]

        return pipelines

    except Exception as e:
        logger.error(f"Failed to list pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED, summary="Create Pipeline")
async def create_pipeline(
    pipeline: PipelineCreate,
    current_user: User = Depends(PermissionChecker("pipeline:create")),
    db: Session = Depends(get_db_session)
) -> PipelineResponse:
    """
    Create a new data pipeline.

    **Required Permission:** `pipeline:create`
    """
    try:
        # Check if pipeline name already exists
        existing = db.execute(
            text("SELECT id FROM pipelines WHERE pipeline_name = :name"),
            {"name": pipeline.pipeline_name}
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pipeline '{pipeline.pipeline_name}' already exists"
            )

        # Insert pipeline
        insert_query = text("""
            INSERT INTO pipelines (
                pipeline_name, pipeline_type, description, owner_user_id,
                is_active, schedule_cron, source_config, destination_config,
                transformation_config, status, tags
            ) VALUES (
                :pipeline_name, :pipeline_type, :description, :owner_user_id,
                :is_active, :schedule_cron, :source_config::jsonb, :destination_config::jsonb,
                :transformation_config::jsonb, :status, :tags
            )
            RETURNING id, pipeline_name, pipeline_type, description, owner_user_id,
                      is_active, schedule_cron, status, last_run_at, last_run_status,
                      last_run_duration_ms, last_run_rows_processed,
                      total_runs, successful_runs, failed_runs,
                      created_at, updated_at, tags
        """)

        import json
        result = db.execute(insert_query, {
            "pipeline_name": pipeline.pipeline_name,
            "pipeline_type": pipeline.pipeline_type,
            "description": pipeline.description,
            "owner_user_id": current_user.id,
            "is_active": True,
            "schedule_cron": pipeline.schedule_cron,
            "source_config": json.dumps(pipeline.source_config),
            "destination_config": json.dumps(pipeline.destination_config),
            "transformation_config": json.dumps(pipeline.transformation_config) if pipeline.transformation_config else None,
            "status": "draft",
            "tags": pipeline.tags or []
        })

        db.commit()
        row = result.fetchone()

        return PipelineResponse(
            id=row[0],
            pipeline_name=row[1],
            pipeline_type=row[2],
            description=row[3],
            owner_user_id=row[4],
            is_active=row[5],
            schedule_cron=row[6],
            status=row[7],
            last_run_at=row[8],
            last_run_status=row[9],
            last_run_duration_ms=row[10],
            last_run_rows_processed=row[11],
            total_runs=row[12],
            successful_runs=row[13],
            failed_runs=row[14],
            created_at=row[15],
            updated_at=row[16],
            tags=row[17] or []
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pipeline_id}", response_model=PipelineResponse, summary="Get Pipeline")
async def get_pipeline(
    pipeline_id: int,
    current_user: User = Depends(PermissionChecker("pipeline:read")),
    db: Session = Depends(get_db_session)
) -> PipelineResponse:
    """
    Get pipeline by ID.

    **Required Permission:** `pipeline:read`
    """
    try:
        result = db.execute(
            text("""
                SELECT
                    id, pipeline_name, pipeline_type, description, owner_user_id,
                    is_active, schedule_cron, status, last_run_at, last_run_status,
                    last_run_duration_ms, last_run_rows_processed,
                    total_runs, successful_runs, failed_runs,
                    created_at, updated_at, tags
                FROM pipelines
                WHERE id = :pipeline_id
            """),
            {"pipeline_id": pipeline_id}
        )

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        return PipelineResponse(
            id=row[0],
            pipeline_name=row[1],
            pipeline_type=row[2],
            description=row[3],
            owner_user_id=row[4],
            is_active=row[5],
            schedule_cron=row[6],
            status=row[7],
            last_run_at=row[8],
            last_run_status=row[9],
            last_run_duration_ms=row[10],
            last_run_rows_processed=row[11],
            total_runs=row[12],
            successful_runs=row[13],
            failed_runs=row[14],
            created_at=row[15],
            updated_at=row[16],
            tags=row[17] or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{pipeline_id}", response_model=PipelineResponse, summary="Update Pipeline")
async def update_pipeline(
    pipeline_id: int,
    pipeline: PipelineUpdate,
    current_user: User = Depends(PermissionChecker("pipeline:create")),
    db: Session = Depends(get_db_session)
) -> PipelineResponse:
    """
    Update pipeline configuration.

    **Required Permission:** `pipeline:create`
    """
    try:
        # Build dynamic UPDATE query
        update_fields = []
        params = {"pipeline_id": pipeline_id}

        if pipeline.description is not None:
            update_fields.append("description = :description")
            params["description"] = pipeline.description

        if pipeline.is_active is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = pipeline.is_active

        if pipeline.schedule_cron is not None:
            update_fields.append("schedule_cron = :schedule_cron")
            params["schedule_cron"] = pipeline.schedule_cron

        if pipeline.tags is not None:
            update_fields.append("tags = :tags")
            params["tags"] = pipeline.tags

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        update_query = text(f"""
            UPDATE pipelines
            SET {", ".join(update_fields)}
            WHERE id = :pipeline_id
            RETURNING id, pipeline_name, pipeline_type, description, owner_user_id,
                      is_active, schedule_cron, status, last_run_at, last_run_status,
                      last_run_duration_ms, last_run_rows_processed,
                      total_runs, successful_runs, failed_runs,
                      created_at, updated_at, tags
        """)

        result = db.execute(update_query, params)
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        db.commit()

        return PipelineResponse(
            id=row[0],
            pipeline_name=row[1],
            pipeline_type=row[2],
            description=row[3],
            owner_user_id=row[4],
            is_active=row[5],
            schedule_cron=row[6],
            status=row[7],
            last_run_at=row[8],
            last_run_status=row[9],
            last_run_duration_ms=row[10],
            last_run_rows_processed=row[11],
            total_runs=row[12],
            successful_runs=row[13],
            failed_runs=row[14],
            created_at=row[15],
            updated_at=row[16],
            tags=row[17] or []
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{pipeline_id}", summary="Delete Pipeline")
async def delete_pipeline(
    pipeline_id: int,
    current_user: User = Depends(PermissionChecker("pipeline:delete")),
    db: Session = Depends(get_db_session)
) -> Dict[str, str]:
    """
    Delete a pipeline.

    **Required Permission:** `pipeline:delete`
    """
    try:
        result = db.execute(
            text("DELETE FROM pipelines WHERE id = :pipeline_id"),
            {"pipeline_id": pipeline_id}
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        db.commit()

        return {"message": f"Pipeline {pipeline_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{pipeline_id}/run", response_model=PipelineRunResponse, summary="Run Pipeline")
async def run_pipeline(
    pipeline_id: int,
    run_request: PipelineRunRequest,
    current_user: User = Depends(PermissionChecker("pipeline:execute")),
    db: Session = Depends(get_db_session)
) -> PipelineRunResponse:
    """
    Execute a pipeline.

    **Required Permission:** `pipeline:execute`

    Note: This is a placeholder that will trigger actual pipeline execution
    when integrated with the pipeline execution engine.
    """
    import uuid

    try:
        # Check pipeline exists
        result = db.execute(
            text("SELECT id, pipeline_name, is_active FROM pipelines WHERE id = :pipeline_id"),
            {"pipeline_id": pipeline_id}
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        if not row[2]:  # is_active
            raise HTTPException(status_code=400, detail="Pipeline is not active")

        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # TODO: Actually trigger pipeline execution
        # For now, just update the pipeline's last_run fields
        db.execute(
            text("""
                UPDATE pipelines
                SET last_run_at = :started_at,
                    last_run_status = 'pending',
                    total_runs = total_runs + 1,
                    status = 'active'
                WHERE id = :pipeline_id
            """),
            {"pipeline_id": pipeline_id, "started_at": started_at}
        )

        db.commit()

        return PipelineRunResponse(
            run_id=run_id,
            pipeline_id=pipeline_id,
            status="pending",
            started_at=started_at,
            message=f"Pipeline {row[1]} execution started"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to run pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
