"""
Agents API Router (v1)

AI agent task management endpoints.
Submit tasks to agents, monitor status, and retrieve results.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, status
from pydantic import BaseModel, Field

from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker
from neurolake.agents.coordinator import TaskQueue, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)
router = APIRouter()

# Global task queue (in production, this would be in Redis or a database)
_task_queue = TaskQueue()


# Pydantic Models
class TaskCreate(BaseModel):
    """Task creation request."""
    description: str = Field(..., min_length=1, max_length=1000, description="Task description")
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    agent_type: Optional[str] = Field(None, description="Specific agent type to use")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Task parameters")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class TaskResponse(BaseModel):
    """Task response."""
    id: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Any = None
    error: Optional[str]
    metadata: Dict[str, Any]


class TaskListResponse(BaseModel):
    """Task list response."""
    tasks: List[TaskResponse]
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int


# Endpoints

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Create Agent Task")
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """
    Submit a new task to the agent system.

    **Required:** Authenticated user

    The task will be added to the queue and processed by an available agent.
    You can monitor task status using the task ID returned.

    Example tasks:
    - "Analyze sales data for trends"
    - "Build a pipeline from CSV to database"
    - "Optimize query performance"
    - "Generate data quality report"
    """
    try:
        # Add user information to metadata
        metadata = task.metadata or {}
        metadata.update({
            "user_id": current_user.id,
            "username": current_user.username,
            "agent_type": task.agent_type,
            "submitted_at": datetime.utcnow().isoformat()
        })

        # Submit task to queue
        task_id = _task_queue.add_task(
            description=task.description,
            priority=task.priority,
            metadata=metadata
        )

        # Get the task back to return details
        task_obj = _task_queue.tasks.get(task_id)

        return TaskResponse(
            id=task_obj.id,
            description=task_obj.description,
            priority=task_obj.priority.name.lower(),
            status=task_obj.status.value,
            assigned_to=task_obj.assigned_to,
            created_at=task_obj.created_at,
            started_at=task_obj.started_at,
            completed_at=task_obj.completed_at,
            result=task_obj.result,
            error=task_obj.error,
            metadata=task_obj.metadata
        )

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TaskListResponse, summary="List Agent Tasks")
async def list_tasks(
    status_filter: Optional[str] = QueryParam(None, description="Filter by status"),
    limit: int = QueryParam(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user)
) -> TaskListResponse:
    """
    Get all agent tasks.

    **Required:** Authenticated user

    Returns list of tasks with their current status. Can filter by status.
    """
    try:
        # Get all tasks
        all_tasks = list(_task_queue.tasks.values())

        # Apply status filter if provided
        if status_filter:
            all_tasks = [
                t for t in all_tasks
                if t.status.value == status_filter
            ]

        # Calculate statistics
        total = len(all_tasks)
        pending = sum(1 for t in all_tasks if t.status == TaskStatus.PENDING)
        in_progress = sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS)
        completed = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in all_tasks if t.status == TaskStatus.FAILED)

        # Sort by created_at descending and apply limit
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        all_tasks = all_tasks[:limit]

        # Convert to response format
        tasks = [
            TaskResponse(
                id=t.id,
                description=t.description,
                priority=t.priority.name.lower(),
                status=t.status.value,
                assigned_to=t.assigned_to,
                created_at=t.created_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                result=t.result,
                error=t.error,
                metadata=t.metadata
            )
            for t in all_tasks
        ]

        return TaskListResponse(
            tasks=tasks,
            total=total,
            pending=pending,
            in_progress=in_progress,
            completed=completed,
            failed=failed
        )

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse, summary="Get Task Status")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """
    Get status and details of a specific task.

    **Required:** Authenticated user

    Use this to monitor task execution progress and retrieve results.
    """
    try:
        task = _task_queue.tasks.get(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return TaskResponse(
            id=task.id,
            description=task.description,
            priority=task.priority.name.lower(),
            status=task.status.value,
            assigned_to=task.assigned_to,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            result=task.result,
            error=task.error,
            metadata=task.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}", summary="Cancel Task")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Cancel a pending or in-progress task.

    **Required:** Authenticated user

    Only tasks that are PENDING or IN_PROGRESS can be cancelled.
    Completed or failed tasks cannot be cancelled.
    """
    try:
        task = _task_queue.tasks.get(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in {task.status.value} status"
            )

        # Cancel the task
        _task_queue.cancel_task(task_id)

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": f"Task {task_id} cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/retry", response_model=TaskResponse, summary="Retry Failed Task")
async def retry_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """
    Retry a failed task.

    **Required:** Authenticated user

    Creates a new task with the same parameters as the failed task.
    Only failed tasks can be retried.
    """
    try:
        task = _task_queue.tasks.get(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task.status != TaskStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail=f"Can only retry failed tasks. Task is {task.status.value}"
            )

        # Create new task with same parameters
        new_task_id = _task_queue.add_task(
            description=f"[RETRY] {task.description}",
            priority=task.priority.name.lower(),
            metadata={
                **task.metadata,
                "retry_of": task_id,
                "retried_at": datetime.utcnow().isoformat()
            }
        )

        new_task = _task_queue.tasks.get(new_task_id)

        return TaskResponse(
            id=new_task.id,
            description=new_task.description,
            priority=new_task.priority.name.lower(),
            status=new_task.status.value,
            assigned_to=new_task.assigned_to,
            created_at=new_task.created_at,
            started_at=new_task.started_at,
            completed_at=new_task.completed_at,
            result=new_task.result,
            error=new_task.error,
            metadata=new_task.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", summary="Get Agent Statistics")
async def get_agent_stats(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get overall agent system statistics.

    **Required:** Authenticated user

    Returns summary statistics about task execution.
    """
    try:
        all_tasks = list(_task_queue.tasks.values())
        completed_tasks = _task_queue.completed_tasks

        total_tasks = len(all_tasks)
        pending = sum(1 for t in all_tasks if t.status == TaskStatus.PENDING)
        in_progress = sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS)
        completed = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in all_tasks if t.status == TaskStatus.FAILED)

        # Calculate average execution time for completed tasks
        execution_times = [
            (t.completed_at - t.started_at).total_seconds()
            for t in completed_tasks
            if t.started_at and t.completed_at
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        return {
            "total_tasks": total_tasks,
            "by_status": {
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed,
                "cancelled": sum(1 for t in all_tasks if t.status == TaskStatus.CANCELLED)
            },
            "success_rate": (completed / total_tasks * 100) if total_tasks > 0 else 0,
            "failure_rate": (failed / total_tasks * 100) if total_tasks > 0 else 0,
            "avg_execution_time_seconds": round(avg_execution_time, 2),
            "queue_depth": pending,
            "active_tasks": in_progress
        }

    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
