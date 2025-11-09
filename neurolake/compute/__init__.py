"""
NeuroLake Compute Engine

Comprehensive compute orchestration supporting:
- Local machine compute (CPU, GPU, Memory)
- Cloud compute (AWS, Azure, GCP)
- Distributed compute (Ray, Dask, Spark)
- Container orchestration (Docker, Kubernetes)
- Auto-scaling and resource optimization
"""

from .local_compute import LocalComputeEngine, ComputeResources
from .cloud_compute import CloudComputeEngine, CloudProvider
from .distributed_compute import DistributedComputeEngine, DistributedFramework
from .compute_orchestrator import (
    ComputeOrchestrator,
    WorkloadType,
    ExecutionTier,
    WorkloadRequest,
    WorkloadResult
)

__all__ = [
    'LocalComputeEngine',
    'CloudComputeEngine',
    'DistributedComputeEngine',
    'ComputeOrchestrator',
    'ComputeResources',
    'CloudProvider',
    'DistributedFramework',
    'WorkloadType',
    'ExecutionTier',
    'WorkloadRequest',
    'WorkloadResult',
]
