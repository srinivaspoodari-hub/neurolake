"""
Hybrid Compute Scheduler

Intelligently schedules workloads between local and cloud compute
resources based on cost, performance, and availability.
"""

import psutil
import logging
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkloadType(str, Enum):
    """Types of compute workloads"""
    QUERY = "query"
    ETL = "etl"
    ML_TRAINING = "ml_training"
    ML_INFERENCE = "ml_inference"
    MIGRATION = "migration"


class ComputeTier(str, Enum):
    """Compute execution tiers"""
    LOCAL = "local"
    CLOUD_SMALL = "cloud_small"
    CLOUD_LARGE = "cloud_large"


class HybridComputeScheduler:
    """
    Schedules compute workloads across local and cloud resources

    Features:
    - Local-first execution for cost savings
    - Cloud burst for heavy workloads
    - Resource monitoring and limits
    - Cost-aware scheduling
    """

    def __init__(
        self,
        local_cpu_limit_pct: float = 80.0,
        local_memory_limit_pct: float = 80.0,
        cloud_enabled: bool = False,
        cost_per_cloud_hour: float = 0.10
    ):
        """
        Initialize Hybrid Compute Scheduler

        Args:
            local_cpu_limit_pct: Max CPU usage % for local execution
            local_memory_limit_pct: Max memory usage % for local execution
            cloud_enabled: Whether cloud compute is available
            cost_per_cloud_hour: Cost per hour for cloud compute
        """
        self.local_cpu_limit = local_cpu_limit_pct
        self.local_memory_limit = local_memory_limit_pct
        self.cloud_enabled = cloud_enabled
        self.cost_per_cloud_hour = cost_per_cloud_hour

        self.stats = {
            'local_executions': 0,
            'cloud_executions': 0,
            'failed_executions': 0,
            'total_local_runtime_seconds': 0,
            'total_cloud_runtime_seconds': 0,
            'estimated_cost_saved_usd': 0.0
        }

        logger.info(f"Hybrid compute scheduler initialized (cloud={'enabled' if cloud_enabled else 'disabled'})")

    def get_local_resources(self) -> Dict[str, Any]:
        """Get current local resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024 ** 3),
                'memory_total_gb': memory.total / (1024 ** 3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 ** 3),
                'is_overloaded': cpu_percent > self.local_cpu_limit or memory.percent > self.local_memory_limit
            }
        except Exception as e:
            logger.error(f"Error getting local resources: {e}")
            return {
                'cpu_percent': 100,
                'memory_percent': 100,
                'is_overloaded': True
            }

    def schedule_workload(
        self,
        workload_type: WorkloadType,
        estimated_cpu: float,  # CPU cores
        estimated_memory_gb: float,
        estimated_duration_minutes: float,
        priority: int = 5  # 1-10, 10=highest
    ) -> Dict[str, Any]:
        """
        Schedule a workload to appropriate compute tier

        Args:
            workload_type: Type of workload
            estimated_cpu: Estimated CPU cores needed
            estimated_memory_gb: Estimated memory in GB
            estimated_duration_minutes: Estimated runtime
            priority: Priority (1-10, higher=more important)

        Returns:
            Scheduling decision
        """
        resources = self.get_local_resources()

        # Decision logic
        can_run_local = (
            not resources['is_overloaded'] and
            estimated_memory_gb < resources['memory_available_gb'] * 0.8 and
            estimated_cpu <= resources['cpu_count']
        )

        # Cost calculation
        local_cost = 0.0  # Free for local
        cloud_cost = (estimated_duration_minutes / 60) * self.cost_per_cloud_hour

        # Decide execution tier
        if can_run_local:
            tier = ComputeTier.LOCAL
            cost = local_cost
            self.stats['estimated_cost_saved_usd'] += cloud_cost
        elif self.cloud_enabled:
            if estimated_cpu > 8 or estimated_memory_gb > 32:
                tier = ComputeTier.CLOUD_LARGE
            else:
                tier = ComputeTier.CLOUD_SMALL
            cost = cloud_cost
        else:
            # Queue for later or reject
            tier = None
            cost = 0.0

        decision = {
            'workload_type': workload_type,
            'tier': tier.value if tier else 'queued',
            'estimated_cost_usd': cost,
            'estimated_duration_minutes': estimated_duration_minutes,
            'priority': priority,
            'scheduled_at': datetime.utcnow().isoformat(),
            'reason': self._get_decision_reason(can_run_local, tier)
        }

        logger.info(f"Scheduled {workload_type} to {decision['tier']}: {decision['reason']}")

        return decision

    def _get_decision_reason(
        self,
        can_run_local: bool,
        tier: Optional[ComputeTier]
    ) -> str:
        """Get human-readable reason for scheduling decision"""
        if tier == ComputeTier.LOCAL:
            return "Local resources available, executing locally for cost savings"
        elif tier in [ComputeTier.CLOUD_SMALL, ComputeTier.CLOUD_LARGE]:
            if not can_run_local:
                return "Local resources insufficient, bursting to cloud"
            else:
                return "Workload requires cloud-scale resources"
        else:
            return "No compute resources available, workload queued"

    def execute_workload(
        self,
        workload_id: str,
        tier: ComputeTier,
        workload_func: callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a workload on the specified tier

        Args:
            workload_id: Unique workload identifier
            tier: Compute tier to execute on
            workload_func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Execution result
        """
        start_time = datetime.utcnow()

        try:
            if tier == ComputeTier.LOCAL:
                result = self._execute_local(workload_func, *args, **kwargs)
                self.stats['local_executions'] += 1
            else:
                result = self._execute_cloud(workload_func, *args, **kwargs)
                self.stats['cloud_executions'] += 1

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            if tier == ComputeTier.LOCAL:
                self.stats['total_local_runtime_seconds'] += duration
            else:
                self.stats['total_cloud_runtime_seconds'] += duration

            return {
                'status': 'success',
                'workload_id': workload_id,
                'tier': tier.value,
                'duration_seconds': duration,
                'result': result
            }

        except Exception as e:
            self.stats['failed_executions'] += 1
            logger.error(f"Workload {workload_id} failed: {e}")
            return {
                'status': 'failed',
                'workload_id': workload_id,
                'tier': tier.value,
                'error': str(e)
            }

    def _execute_local(self, workload_func: callable, *args, **kwargs):
        """Execute workload locally"""
        logger.info("Executing workload locally...")
        return workload_func(*args, **kwargs)

    def _execute_cloud(self, workload_func: callable, *args, **kwargs):
        """Execute workload in cloud"""
        logger.info("Executing workload in cloud (placeholder)...")
        # In production, this would submit to cloud compute (Lambda, Batch, etc.)
        return workload_func(*args, **kwargs)

    def get_statistics(self) -> Dict[str, Any]:
        """Get compute scheduler statistics"""
        total_executions = self.stats['local_executions'] + self.stats['cloud_executions']

        return {
            **self.stats,
            'total_executions': total_executions,
            'local_execution_pct': (
                (self.stats['local_executions'] / total_executions * 100)
                if total_executions > 0 else 0
            ),
            'average_local_duration_seconds': (
                self.stats['total_local_runtime_seconds'] / self.stats['local_executions']
                if self.stats['local_executions'] > 0 else 0
            ),
            'average_cloud_duration_seconds': (
                self.stats['total_cloud_runtime_seconds'] / self.stats['cloud_executions']
                if self.stats['cloud_executions'] > 0 else 0
            )
        }
