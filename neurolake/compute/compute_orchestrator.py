"""
Compute Orchestrator

Main orchestration layer that intelligently routes workloads across:
- Local compute
- Cloud compute (AWS, Azure, GCP)
- Distributed frameworks (Ray, Dask, Spark)

Provides unified API and smart routing based on workload characteristics.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .local_compute import LocalComputeEngine, ComputeResources
from .cloud_compute import CloudComputeEngine, CloudProvider, ComputeService
from .distributed_compute import DistributedComputeEngine, DistributedFramework

# Import environment manager
try:
    from neurolake.config import get_environment_manager
    ENVIRONMENT_MANAGER_AVAILABLE = True
except ImportError:
    ENVIRONMENT_MANAGER_AVAILABLE = False
    logger.warning("Environment manager not available")

logger = logging.getLogger(__name__)


class WorkloadType(str, Enum):
    """Types of compute workloads"""
    SQL_QUERY = "sql_query"
    DATA_TRANSFORMATION = "data_transformation"
    ETL = "etl"
    ML_TRAINING = "ml_training"
    ML_INFERENCE = "ml_inference"
    DATA_MIGRATION = "data_migration"
    ANALYTICS = "analytics"
    STREAMING = "streaming"


class ExecutionTier(str, Enum):
    """Execution tiers"""
    LOCAL = "local"
    LOCAL_DISTRIBUTED = "local_distributed"
    CLOUD_SERVERLESS = "cloud_serverless"
    CLOUD_CONTAINER = "cloud_container"
    CLOUD_SPARK = "cloud_spark"
    HYBRID = "hybrid"


@dataclass
class WorkloadRequest:
    """Workload execution request"""
    workload_id: str
    workload_type: WorkloadType
    function: Optional[Callable]
    args: tuple
    kwargs: dict

    # Resource requirements
    required_cpu_cores: float
    required_memory_gb: float
    required_gpu: bool
    estimated_duration_minutes: float

    # Preferences
    prefer_local: bool
    max_cost_usd: Optional[float]
    deadline: Optional[str]

    # Data
    data_size_gb: Optional[float]
    data_location: Optional[str]


@dataclass
class WorkloadResult:
    """Workload execution result"""
    workload_id: str
    status: str
    execution_tier: ExecutionTier
    provider: Optional[str]
    service: Optional[str]
    job_id: Optional[str]

    # Timing
    submitted_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]

    # Resources used
    actual_cpu_cores: Optional[float]
    actual_memory_gb: Optional[float]

    # Cost
    estimated_cost_usd: float
    actual_cost_usd: Optional[float]

    # Result
    result: Optional[Any]
    error: Optional[str]


class ComputeOrchestrator:
    """
    Compute Orchestrator

    Intelligently routes workloads across local, cloud, and distributed compute.
    """

    def __init__(
        self,
        enable_cloud: bool = True,
        enable_distributed: bool = True,
        default_cloud_provider: Optional[CloudProvider] = CloudProvider.AWS,
        memory_overhead_percent: float = 40.0,
        user_permissions: Optional[List[str]] = None
    ):
        """
        Initialize compute orchestrator with environment enforcement

        Args:
            enable_cloud: Enable cloud compute
            enable_distributed: Enable distributed frameworks
            default_cloud_provider: Default cloud provider
            memory_overhead_percent: Memory overhead to reserve (default 40%)
            user_permissions: User permissions for RBAC checks
        """
        # Get environment manager
        self.env_manager = get_environment_manager() if ENVIRONMENT_MANAGER_AVAILABLE else None
        self.user_permissions = user_permissions or []

        # Production enforcement: If in production, force cloud-only
        if self.env_manager and self.env_manager.is_production():
            logger.warning("PRODUCTION MODE: Enforcing cloud-only compute")
            enable_cloud = True  # Must enable cloud
            # Local engine only for monitoring, not execution
            self.local_execution_allowed = False
        else:
            # Check if local compute is allowed
            if self.env_manager:
                local_check = self.env_manager.can_use_local_compute(self.user_permissions)
                self.local_execution_allowed = local_check['allowed']
                if not local_check['allowed']:
                    logger.info(f"Local compute disabled: {local_check['reason']}")
            else:
                self.local_execution_allowed = True

        # Initialize engines
        self.local_engine = LocalComputeEngine()  # Always init for monitoring
        self.cloud_engine = CloudComputeEngine() if enable_cloud else None
        self.distributed_engine = DistributedComputeEngine() if enable_distributed else None

        self.enable_cloud = enable_cloud
        self.enable_distributed = enable_distributed
        self.default_cloud_provider = default_cloud_provider
        self.memory_overhead_percent = memory_overhead_percent

        # Tracking
        self.workload_history: List[WorkloadResult] = []
        self.active_workloads: Dict[str, WorkloadResult] = {}

        logger.info("Compute orchestrator initialized")
        logger.info(f"Environment: {self.env_manager.current_env.value if self.env_manager else 'unknown'}")
        logger.info(f"Local execution: {'allowed' if self.local_execution_allowed else 'DISABLED (cloud-only)'}")
        logger.info(f"Cloud: {'enabled' if enable_cloud else 'disabled'}")
        logger.info(f"Distributed: {'enabled' if enable_distributed else 'disabled'}")
        logger.info(f"Memory overhead: {memory_overhead_percent}% (usable: {100-memory_overhead_percent}%)")

    def execute(self, request: WorkloadRequest) -> WorkloadResult:
        """
        Execute workload with intelligent routing

        Args:
            request: Workload request

        Returns:
            Workload result
        """
        logger.info(f"Executing workload: {request.workload_id} ({request.workload_type.value})")

        # Determine execution tier
        tier, decision = self._route_workload(request)

        logger.info(f"Routed to {tier.value}: {decision['reason']}")

        # Execute on selected tier
        result = self._execute_on_tier(request, tier, decision)

        # Track result
        self.workload_history.append(result)

        return result

    def _route_workload(
        self,
        request: WorkloadRequest
    ) -> tuple[ExecutionTier, Dict[str, Any]]:
        """Route workload to appropriate execution tier"""

        # Check local capacity with dynamic memory allocation
        local_check = self.local_engine.can_handle_workload(
            required_cpu_cores=request.required_cpu_cores,
            required_memory_gb=request.required_memory_gb,
            required_gpu=request.required_gpu,
            memory_overhead_percent=self.memory_overhead_percent
        )

        # Decision factors
        factors = {
            'local_available': local_check['can_handle'],
            'local_execution_allowed': self.local_execution_allowed,  # Production enforcement
            'prefer_local': request.prefer_local,
            'cloud_enabled': self.enable_cloud,
            'distributed_enabled': self.enable_distributed,
            'gpu_required': request.required_gpu,
            'large_data': request.data_size_gb and request.data_size_gb > 10,
            'workload_type': request.workload_type,
            'is_production': self.env_manager.is_production() if self.env_manager else False
        }

        # PRODUCTION ENFORCEMENT: Force cloud-only
        if factors['is_production'] or not factors['local_execution_allowed']:
            logger.info("Production/policy enforced: Routing to cloud")
            if request.workload_type == WorkloadType.ML_TRAINING:
                tier = ExecutionTier.CLOUD_SPARK
                reason = "Production mode: ML training on cloud Spark"
            elif request.workload_type in [WorkloadType.SQL_QUERY, WorkloadType.ML_INFERENCE]:
                tier = ExecutionTier.CLOUD_SERVERLESS
                reason = "Production mode: Serverless compute"
            else:
                tier = ExecutionTier.CLOUD_CONTAINER
                reason = "Production mode: Cloud containers"

        # Routing logic (only if local execution allowed)
        elif factors['local_available'] and factors['prefer_local']:
            # Local execution preferred and possible
            if factors['distributed_enabled'] and factors['large_data']:
                tier = ExecutionTier.LOCAL_DISTRIBUTED
                reason = "Large dataset - using local distributed framework"
            else:
                tier = ExecutionTier.LOCAL
                reason = "Local resources available, executing locally"

        elif factors['local_available'] and not factors['cloud_enabled']:
            # Local only option
            tier = ExecutionTier.LOCAL
            reason = "Cloud disabled, executing locally"

        elif not factors['local_available'] and factors['cloud_enabled']:
            # Cloud execution required
            if request.workload_type == WorkloadType.ML_TRAINING:
                tier = ExecutionTier.CLOUD_SPARK
                reason = "ML training requires cloud Spark cluster"
            elif request.workload_type in [WorkloadType.SQL_QUERY, WorkloadType.ML_INFERENCE]:
                tier = ExecutionTier.CLOUD_SERVERLESS
                reason = "Quick workload - using serverless compute"
            else:
                tier = ExecutionTier.CLOUD_CONTAINER
                reason = "Local resources insufficient, using cloud containers"

        elif factors['cloud_enabled'] and request.max_cost_usd and request.max_cost_usd < 0.01:
            # Cost-sensitive workload
            tier = ExecutionTier.LOCAL
            reason = "Cost optimization - using free local resources"

        else:
            # Hybrid approach
            tier = ExecutionTier.HYBRID
            reason = "Using hybrid execution for optimal performance"

        decision = {
            'tier': tier,
            'reason': reason,
            'factors': factors,
            'estimated_cost_usd': self._estimate_cost(request, tier)
        }

        return tier, decision

    def _execute_on_tier(
        self,
        request: WorkloadRequest,
        tier: ExecutionTier,
        decision: Dict[str, Any]
    ) -> WorkloadResult:
        """Execute workload on specified tier"""
        start_time = datetime.now()

        result = WorkloadResult(
            workload_id=request.workload_id,
            status='submitted',
            execution_tier=tier,
            provider=None,
            service=None,
            job_id=None,
            submitted_at=start_time.isoformat(),
            started_at=None,
            completed_at=None,
            duration_seconds=None,
            actual_cpu_cores=None,
            actual_memory_gb=None,
            estimated_cost_usd=decision['estimated_cost_usd'],
            actual_cost_usd=None,
            result=None,
            error=None
        )

        self.active_workloads[request.workload_id] = result

        try:
            if tier == ExecutionTier.LOCAL:
                exec_result = self._execute_local(request)

            elif tier == ExecutionTier.LOCAL_DISTRIBUTED:
                exec_result = self._execute_local_distributed(request)

            elif tier in [ExecutionTier.CLOUD_SERVERLESS, ExecutionTier.CLOUD_CONTAINER, ExecutionTier.CLOUD_SPARK]:
                exec_result = self._execute_cloud(request, tier)

            elif tier == ExecutionTier.HYBRID:
                exec_result = self._execute_hybrid(request)

            else:
                raise ValueError(f"Unsupported tier: {tier}")

            # Update result
            end_time = datetime.now()
            result.status = 'completed'
            result.started_at = start_time.isoformat()
            result.completed_at = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.result = exec_result.get('result')
            result.provider = exec_result.get('provider')
            result.service = exec_result.get('service')
            result.job_id = exec_result.get('job_id')

        except Exception as e:
            logger.error(f"Workload {request.workload_id} failed: {e}")
            result.status = 'failed'
            result.error = str(e)

        finally:
            del self.active_workloads[request.workload_id]

        return result

    def _execute_local(self, request: WorkloadRequest) -> Dict[str, Any]:
        """Execute on local machine"""
        if request.function:
            result = request.function(*request.args, **request.kwargs)
            return {
                'result': result,
                'execution_mode': 'local'
            }
        else:
            return {
                'result': f"Mock execution for {request.workload_type.value}",
                'execution_mode': 'local'
            }

    def _execute_local_distributed(self, request: WorkloadRequest) -> Dict[str, Any]:
        """Execute using local distributed framework"""
        if not self.distributed_engine:
            logger.warning("Distributed engine not available, falling back to local")
            return self._execute_local(request)

        # Try Ray first, then Dask
        available = self.distributed_engine.get_available_frameworks()

        if available.get('ray'):
            logger.info("Using Ray for distributed execution")
            if DistributedFramework.RAY not in self.distributed_engine.active_clusters:
                self.distributed_engine.initialize_ray()

            result = self.distributed_engine.submit_ray_task(
                request.function,
                *request.args,
                **request.kwargs
            )
            return {
                'result': result,
                'execution_mode': 'distributed_ray'
            }

        elif available.get('dask'):
            logger.info("Using Dask for distributed execution")
            if DistributedFramework.DASK not in self.distributed_engine.active_clusters:
                self.distributed_engine.initialize_dask()

            result = self.distributed_engine.submit_dask_task(
                request.function,
                *request.args,
                **request.kwargs
            )
            return {
                'result': result,
                'execution_mode': 'distributed_dask'
            }

        else:
            logger.warning("No distributed framework available, falling back to local")
            return self._execute_local(request)

    def _execute_cloud(self, request: WorkloadRequest, tier: ExecutionTier) -> Dict[str, Any]:
        """Execute on cloud"""
        if not self.cloud_engine:
            raise RuntimeError("Cloud engine not available")

        provider = self.default_cloud_provider

        # Select service based on tier
        if tier == ExecutionTier.CLOUD_SERVERLESS:
            if provider == CloudProvider.AWS:
                service = ComputeService.AWS_LAMBDA
            elif provider == CloudProvider.AZURE:
                service = ComputeService.AZURE_FUNCTIONS
            else:
                service = ComputeService.GCP_CLOUD_FUNCTIONS

        elif tier == ExecutionTier.CLOUD_CONTAINER:
            if provider == CloudProvider.AWS:
                service = ComputeService.AWS_ECS
            elif provider == CloudProvider.AZURE:
                service = ComputeService.AZURE_CONTAINER_INSTANCES
            else:
                service = ComputeService.GCP_CLOUD_RUN

        elif tier == ExecutionTier.CLOUD_SPARK:
            if provider == CloudProvider.AWS:
                service = ComputeService.AWS_EMR
            elif provider == CloudProvider.AZURE:
                service = ComputeService.AZURE_DATABRICKS
            else:
                service = ComputeService.GCP_DATAPROC

        else:
            service = None

        # Submit to cloud
        workload_config = {
            'workload_id': request.workload_id,
            'workload_type': request.workload_type.value,
            'function_name': request.function.__name__ if request.function else 'unknown'
        }

        submission = self.cloud_engine.submit_workload(
            provider=provider,
            service=service,
            workload_config=workload_config
        )

        return submission

    def _execute_hybrid(self, request: WorkloadRequest) -> Dict[str, Any]:
        """Execute using hybrid approach"""
        # For now, default to local execution
        # In production, this would split workload intelligently
        logger.info("Hybrid execution: using local for now")
        return self._execute_local(request)

    def _estimate_cost(self, request: WorkloadRequest, tier: ExecutionTier) -> float:
        """Estimate execution cost"""
        if tier == ExecutionTier.LOCAL:
            return 0.0
        elif tier == ExecutionTier.LOCAL_DISTRIBUTED:
            return 0.0
        elif tier == ExecutionTier.CLOUD_SERVERLESS:
            # Lambda pricing example
            duration_hours = request.estimated_duration_minutes / 60
            return duration_hours * 0.01  # $0.01/hour approximation
        elif tier == ExecutionTier.CLOUD_CONTAINER:
            duration_hours = request.estimated_duration_minutes / 60
            return duration_hours * 0.05  # $0.05/hour approximation
        elif tier == ExecutionTier.CLOUD_SPARK:
            duration_hours = request.estimated_duration_minutes / 60
            return duration_hours * 0.20  # $0.20/hour approximation
        else:
            return 0.0

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        if not self.workload_history:
            return {
                'total_workloads': 0,
                'by_tier': {},
                'by_status': {},
                'total_cost_usd': 0.0
            }

        total = len(self.workload_history)
        by_tier = {}
        by_status = {}
        total_cost = 0.0

        for workload in self.workload_history:
            # By tier
            tier = workload.execution_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

            # By status
            status = workload.status
            by_status[status] = by_status.get(status, 0) + 1

            # Cost
            total_cost += workload.estimated_cost_usd

        return {
            'total_workloads': total,
            'active_workloads': len(self.active_workloads),
            'by_tier': by_tier,
            'by_status': by_status,
            'total_cost_usd': total_cost,
            'average_duration_seconds': sum(
                w.duration_seconds for w in self.workload_history if w.duration_seconds
            ) / total if total > 0 else 0
        }

    def get_local_resources(self) -> ComputeResources:
        """Get current local resources"""
        return self.local_engine.get_resources()

    def configure_cloud_provider(
        self,
        provider: CloudProvider,
        **credentials
    ) -> bool:
        """Configure a cloud provider"""
        if not self.cloud_engine:
            logger.error("Cloud engine not enabled")
            return False

        if provider == CloudProvider.AWS:
            return self.cloud_engine.configure_aws(**credentials)
        elif provider == CloudProvider.AZURE:
            return self.cloud_engine.configure_azure(**credentials)
        elif provider == CloudProvider.GCP:
            return self.cloud_engine.configure_gcp(**credentials)

        return False

    def get_configured_providers(self) -> List[Dict[str, Any]]:
        """Get configured cloud providers"""
        if not self.cloud_engine:
            return []

        return self.cloud_engine.get_configured_providers()

    def get_dynamic_memory_allocation(self) -> Dict[str, float]:
        """
        Get dynamic memory allocation based on current system state.

        Returns memory that can be safely allocated after reserving
        the configured overhead percentage for system stability.
        """
        return self.local_engine.get_dynamic_memory_allocation(
            overhead_percent=self.memory_overhead_percent
        )
