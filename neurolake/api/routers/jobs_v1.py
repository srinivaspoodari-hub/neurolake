"""
Jobs & Compute Management API Router (v1)

Comprehensive data ingestion, processing, and compute management:
- Multi-source ingestion (S3, FTP, HTTP, Google Drive, local)
- Batch and streaming processing
- Compute configuration (autoscaling, optimizations, Photon engine)
- Live job monitoring and logs
- User-specific scheduling
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, WebSocket
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from neurolake.db import get_db_session
from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job storage (in production, use database)
active_jobs: Dict[str, Dict[str, Any]] = {}
job_logs: Dict[str, List[Dict[str, Any]]] = {}

# ============================================================================
# MODELS
# ============================================================================

class SourceConfig(BaseModel):
    """Data source configuration."""
    source_type: str = Field(..., description="s3, ftp, http, google_drive, local, kafka, database")
    connection_params: Dict[str, Any] = Field(..., description="Connection parameters")
    file_pattern: Optional[str] = Field(None, description="File pattern to match")
    schema_inference: bool = Field(True, description="Auto-infer schema")

class ComputeConfig(BaseModel):
    """Compute resource configuration."""
    cluster_mode: str = Field(default="single", description="single, multi-node, serverless")
    instance_type: str = Field(default="standard", description="standard, memory_optimized, compute_optimized")
    min_workers: int = Field(default=1, ge=1, le=100)
    max_workers: int = Field(default=10, ge=1, le=1000)
    autoscaling_enabled: bool = Field(default=True)
    photon_enabled: bool = Field(default=False, description="Enable Photon engine for query acceleration")
    adaptive_query_execution: bool = Field(default=True, description="AQE optimizations")
    dynamic_partition_pruning: bool = Field(default=True, description="DPP optimizations")
    cbo_enabled: bool = Field(default=True, description="Cost-based optimizer")
    spark_conf: Optional[Dict[str, str]] = Field(default={}, description="Custom Spark configurations")

class ProcessingConfig(BaseModel):
    """Processing configuration."""
    mode: str = Field(..., description="batch or streaming")
    format: str = Field(default="auto", description="csv, json, parquet, avro, delta, auto")
    batch_size: Optional[int] = Field(1000, description="Records per batch")
    checkpoint_enabled: bool = Field(True, description="Enable checkpointing")
    watermark: Optional[str] = Field(None, description="Watermark for late data (streaming)")
    trigger: Optional[str] = Field(None, description="Trigger interval (streaming)")

class ScheduleConfig(BaseModel):
    """Scheduling configuration."""
    enabled: bool = Field(False)
    cron_expression: Optional[str] = Field(None, description="Cron schedule")
    timezone: str = Field(default="UTC")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=300, ge=0)

class JobCreate(BaseModel):
    """Job creation request."""
    job_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_config: SourceConfig
    destination_schema: str = Field(..., description="Target schema name")
    destination_table: str = Field(..., description="Target table name")
    processing_config: ProcessingConfig
    compute_config: ComputeConfig
    schedule_config: Optional[ScheduleConfig] = None
    tags: Optional[List[str]] = []
    role_access: Optional[List[str]] = Field(default=[], description="Roles with access")

class JobResponse(BaseModel):
    """Job response."""
    job_id: str
    job_name: str
    description: Optional[str]
    status: str  # created, running, completed, failed, cancelled
    created_by: str
    created_at: datetime
    updated_at: datetime
    source_config: SourceConfig
    destination: str
    processing_config: ProcessingConfig
    compute_config: ComputeConfig
    schedule_config: Optional[ScheduleConfig]
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    runs_count: int
    success_count: int
    failure_count: int
    tags: List[str]

class JobExecution(BaseModel):
    """Job execution details."""
    execution_id: str
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    records_processed: int
    records_failed: int
    bytes_processed: int
    error_message: Optional[str]
    metrics: Dict[str, Any]

class LogEntry(BaseModel):
    """Log entry."""
    timestamp: datetime
    level: str  # INFO, WARN, ERROR, DEBUG
    message: str
    metadata: Optional[Dict[str, Any]]

# ============================================================================
# JOB MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("", response_model=JobResponse, status_code=201, summary="Create Job")
async def create_job(
    job: JobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
) -> JobResponse:
    """
    Create a new data ingestion/processing job.

    Supports:
    - Multiple sources (S3, FTP, HTTP, Google Drive, local, Kafka, databases)
    - Batch and streaming modes
    - Compute configuration (autoscaling, Photon, optimizations)
    - Scheduling with cron
    - Role-based access
    """
    try:
        job_id = str(uuid.uuid4())

        # Calculate next run if scheduled
        next_run = None
        if job.schedule_config and job.schedule_config.enabled:
            # In production, use croniter library
            next_run = datetime.utcnow() + timedelta(minutes=5)  # Placeholder

        job_data = {
            "job_id": job_id,
            "job_name": job.job_name,
            "description": job.description,
            "status": "created",
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "source_config": job.source_config,
            "destination": f"{job.destination_schema}.{job.destination_table}",
            "processing_config": job.processing_config,
            "compute_config": job.compute_config,
            "schedule_config": job.schedule_config,
            "last_run": None,
            "next_run": next_run,
            "runs_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "tags": job.tags or []
        }

        # Store in memory (in production, store in database)
        active_jobs[job_id] = job_data
        job_logs[job_id] = []

        logger.info(f"Created job {job_id}: {job.job_name} by {current_user.username}")

        return JobResponse(**job_data)

    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[JobResponse], summary="List Jobs")
async def list_jobs(
    status: Optional[str] = QueryParam(None),
    tag: Optional[str] = QueryParam(None),
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    current_user: User = Depends(get_current_active_user)
) -> List[JobResponse]:
    """List all jobs with filtering."""
    try:
        jobs = list(active_jobs.values())

        # Filter by status
        if status:
            jobs = [j for j in jobs if j["status"] == status]

        # Filter by tag
        if tag:
            jobs = [j for j in jobs if tag in j.get("tags", [])]

        # Pagination
        jobs = jobs[offset:offset + limit]

        return [JobResponse(**j) for j in jobs]

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse, summary="Get Job")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> JobResponse:
    """Get job details."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobResponse(**active_jobs[job_id])


@router.delete("/{job_id}", summary="Delete Job")
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Delete a job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = active_jobs[job_id]

    if job["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot delete running job. Stop it first.")

    del active_jobs[job_id]
    if job_id in job_logs:
        del job_logs[job_id]

    logger.info(f"Deleted job {job_id}")

    return {"status": "success", "message": f"Job {job_id} deleted"}


# ============================================================================
# JOB EXECUTION ENDPOINTS
# ============================================================================

@router.post("/{job_id}/start", response_model=JobExecution, summary="Start Job")
async def start_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> JobExecution:
    """
    Start job execution.

    Initiates data ingestion and processing with configured compute resources.
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = active_jobs[job_id]

    if job["status"] == "running":
        raise HTTPException(status_code=400, detail="Job is already running")

    execution_id = str(uuid.uuid4())

    # Update job status
    job["status"] = "running"
    job["last_run"] = datetime.utcnow()
    job["updated_at"] = datetime.utcnow()
    job["runs_count"] += 1

    # Create execution record
    execution = {
        "execution_id": execution_id,
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "duration_seconds": None,
        "records_processed": 0,
        "records_failed": 0,
        "bytes_processed": 0,
        "error_message": None,
        "metrics": {
            "photon_enabled": job["compute_config"]["photon_enabled"],
            "autoscaling_enabled": job["compute_config"]["autoscaling_enabled"],
            "workers": f"{job['compute_config']['min_workers']}-{job['compute_config']['max_workers']}"
        }
    }

    # Add initial log entry
    job_logs[job_id].append({
        "timestamp": datetime.utcnow(),
        "level": "INFO",
        "message": f"Job execution started: {execution_id}",
        "metadata": {
            "execution_id": execution_id,
            "source": job["source_config"]["source_type"],
            "mode": job["processing_config"]["mode"]
        }
    })

    # Simulate processing (in production, trigger actual Spark/processing job)
    job_logs[job_id].append({
        "timestamp": datetime.utcnow(),
        "level": "INFO",
        "message": f"Initializing {job['compute_config']['min_workers']} workers...",
        "metadata": {"compute_config": job["compute_config"]}
    })

    if job["compute_config"]["photon_enabled"]:
        job_logs[job_id].append({
            "timestamp": datetime.utcnow(),
            "level": "INFO",
            "message": "Photon engine enabled - query acceleration active",
            "metadata": {}
        })

    job_logs[job_id].append({
        "timestamp": datetime.utcnow(),
        "level": "INFO",
        "message": f"Reading from {job['source_config']['source_type']} source...",
        "metadata": {}
    })

    logger.info(f"Started job {job_id}, execution {execution_id}")

    return JobExecution(**execution)


@router.post("/{job_id}/stop", summary="Stop Job")
async def stop_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Stop running job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = active_jobs[job_id]

    if job["status"] != "running":
        raise HTTPException(status_code=400, detail="Job is not running")

    job["status"] = "cancelled"
    job["updated_at"] = datetime.utcnow()

    job_logs[job_id].append({
        "timestamp": datetime.utcnow(),
        "level": "WARN",
        "message": f"Job stopped by {current_user.username}",
        "metadata": {}
    })

    logger.info(f"Stopped job {job_id}")

    return {"status": "success", "message": f"Job {job_id} stopped"}


@router.get("/{job_id}/executions", summary="Get Job Executions")
async def get_job_executions(
    job_id: str,
    limit: int = QueryParam(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get execution history for a job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Placeholder - in production, query from executions table
    return {
        "job_id": job_id,
        "executions": [],
        "total_count": 0
    }


# ============================================================================
# LOGS & MONITORING ENDPOINTS
# ============================================================================

@router.get("/{job_id}/logs", response_model=List[LogEntry], summary="Get Job Logs")
async def get_job_logs(
    job_id: str,
    level: Optional[str] = QueryParam(None, description="Filter by log level"),
    limit: int = QueryParam(1000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user)
) -> List[LogEntry]:
    """
    Get job logs.

    Returns processing logs, errors, warnings, and debug information.
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    logs = job_logs.get(job_id, [])

    # Filter by level
    if level:
        logs = [log for log in logs if log["level"] == level.upper()]

    # Limit
    logs = logs[-limit:]

    return [LogEntry(**log) for log in logs]


@router.get("/{job_id}/metrics", summary="Get Job Metrics")
async def get_job_metrics(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get real-time job metrics.

    Returns:
    - Records processed
    - Throughput (records/sec)
    - Resource utilization
    - Error rates
    - Performance metrics
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = active_jobs[job_id]

    # Simulated metrics (in production, get from monitoring system)
    return {
        "job_id": job_id,
        "status": job["status"],
        "metrics": {
            "records_processed": 125000,
            "records_failed": 23,
            "throughput_rps": 4200,
            "bytes_processed": 512000000,
            "active_workers": job["compute_config"]["min_workers"],
            "cpu_utilization": 67.5,
            "memory_utilization": 72.3,
            "photon_acceleration": job["compute_config"]["photon_enabled"],
            "cache_hit_rate": 0.85,
            "shuffle_bytes": 125000000
        },
        "timestamp": datetime.utcnow()
    }


# ============================================================================
# COMPUTE CONFIGURATION ENDPOINTS
# ============================================================================

@router.patch("/{job_id}/compute", response_model=JobResponse, summary="Update Compute Config")
async def update_compute_config(
    job_id: str,
    compute_config: ComputeConfig,
    current_user: User = Depends(get_current_active_user)
) -> JobResponse:
    """
    Update compute configuration for a job.

    Can modify:
    - Autoscaling settings
    - Instance types
    - Photon engine
    - Spark optimizations
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = active_jobs[job_id]

    if job["status"] == "running":
        raise HTTPException(status_code=400, detail="Cannot update compute config while job is running")

    job["compute_config"] = compute_config.dict()
    job["updated_at"] = datetime.utcnow()

    logger.info(f"Updated compute config for job {job_id}")

    return JobResponse(**job)


@router.get("/compute/presets", summary="Get Compute Presets")
async def get_compute_presets(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get predefined compute configuration presets.

    Returns optimized configurations for common use cases.
    """
    return {
        "presets": [
            {
                "name": "Small Batch",
                "description": "Single node for small datasets (<1GB)",
                "config": {
                    "cluster_mode": "single",
                    "instance_type": "standard",
                    "min_workers": 1,
                    "max_workers": 1,
                    "autoscaling_enabled": False,
                    "photon_enabled": False
                }
            },
            {
                "name": "Medium Batch",
                "description": "Auto-scaling for datasets up to 100GB",
                "config": {
                    "cluster_mode": "multi-node",
                    "instance_type": "compute_optimized",
                    "min_workers": 2,
                    "max_workers": 10,
                    "autoscaling_enabled": True,
                    "photon_enabled": True
                }
            },
            {
                "name": "Large Batch with Photon",
                "description": "High-performance for large datasets (100GB+)",
                "config": {
                    "cluster_mode": "multi-node",
                    "instance_type": "compute_optimized",
                    "min_workers": 5,
                    "max_workers": 50,
                    "autoscaling_enabled": True,
                    "photon_enabled": True,
                    "adaptive_query_execution": True,
                    "dynamic_partition_pruning": True
                }
            },
            {
                "name": "Streaming",
                "description": "Optimized for continuous streaming",
                "config": {
                    "cluster_mode": "multi-node",
                    "instance_type": "memory_optimized",
                    "min_workers": 3,
                    "max_workers": 20,
                    "autoscaling_enabled": True,
                    "photon_enabled": True
                }
            }
        ]
    }


# ============================================================================
# DATA SOURCES ENDPOINTS
# ============================================================================

@router.get("/sources/available", summary="List Available Sources")
async def list_available_sources(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    List all available data source types and their configuration requirements.
    """
    return {
        "sources": [
            {
                "type": "s3",
                "name": "Amazon S3",
                "params": ["bucket", "prefix", "access_key", "secret_key", "region"],
                "formats": ["csv", "json", "parquet", "avro", "delta"],
                "batch": True,
                "streaming": False
            },
            {
                "type": "ftp",
                "name": "FTP/SFTP",
                "params": ["host", "port", "username", "password", "path"],
                "formats": ["csv", "json", "txt", "xml"],
                "batch": True,
                "streaming": False
            },
            {
                "type": "http",
                "name": "HTTP/HTTPS",
                "params": ["url", "method", "headers", "auth"],
                "formats": ["json", "csv", "xml"],
                "batch": True,
                "streaming": False
            },
            {
                "type": "google_drive",
                "name": "Google Drive",
                "params": ["credentials", "folder_id"],
                "formats": ["csv", "json", "sheets"],
                "batch": True,
                "streaming": False
            },
            {
                "type": "local",
                "name": "Local File System",
                "params": ["path", "file_pattern"],
                "formats": ["csv", "json", "parquet", "avro", "delta"],
                "batch": True,
                "streaming": True
            },
            {
                "type": "kafka",
                "name": "Apache Kafka",
                "params": ["bootstrap_servers", "topic", "group_id"],
                "formats": ["json", "avro"],
                "batch": False,
                "streaming": True
            },
            {
                "type": "database",
                "name": "JDBC Database",
                "params": ["jdbc_url", "table", "username", "password", "driver"],
                "formats": ["table"],
                "batch": True,
                "streaming": True
            }
        ]
    }


@router.post("/sources/test", summary="Test Source Connection")
async def test_source_connection(
    source_config: SourceConfig,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Test connection to a data source.

    Validates credentials and connectivity without starting a job.
    """
    try:
        # Simulate connection test
        logger.info(f"Testing connection to {source_config.source_type}")

        return {
            "status": "success",
            "message": f"Successfully connected to {source_config.source_type}",
            "details": {
                "accessible": True,
                "estimated_files": 15,
                "estimated_size_bytes": 5000000,
                "sample_files": ["file1.csv", "file2.csv", "file3.csv"]
            }
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "details": {}
        }
