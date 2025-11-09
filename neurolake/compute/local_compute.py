"""
Local Compute Engine

Detects, mounts, and manages local machine compute resources including:
- CPU cores and threads
- GPU (NVIDIA, AMD)
- Memory (RAM)
- Disk I/O
- Network bandwidth
"""

import psutil
import platform
import os
import subprocess
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ComputeResources:
    """Local compute resources"""
    # CPU
    cpu_count_physical: int
    cpu_count_logical: int
    cpu_freq_current_mhz: float
    cpu_freq_max_mhz: float
    cpu_usage_percent: float
    cpu_per_core_usage: List[float]

    # GPU
    gpu_available: bool
    gpu_count: int
    gpu_devices: List[Dict[str, Any]]
    gpu_total_memory_gb: float

    # Memory
    memory_total_gb: float
    memory_available_gb: float
    memory_used_gb: float
    memory_percent: float
    swap_total_gb: float
    swap_used_gb: float

    # Disk
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    disk_io_read_mb_s: float
    disk_io_write_mb_s: float

    # Network
    network_sent_mb: float
    network_recv_mb: float
    network_interfaces: List[str]

    # System
    platform: str
    platform_version: str
    hostname: str
    boot_time: str
    uptime_hours: float

    # Docker/Containers
    docker_available: bool
    docker_version: Optional[str]
    containers_running: int

    # Timestamp
    measured_at: str


class LocalComputeEngine:
    """
    Local Compute Engine

    Detects and manages local machine compute resources.
    Provides mounting capabilities for workload execution.
    """

    def __init__(self):
        """Initialize local compute engine"""
        self.platform = platform.system()
        self.hostname = platform.node()
        self.boot_time = datetime.fromtimestamp(psutil.boot_time())

        # Track historical metrics
        self.metrics_history: List[ComputeResources] = []
        self.max_history = 100

        # Check GPU availability
        self.gpu_available = self._detect_gpu()

        # Check Docker availability
        self.docker_available = self._detect_docker()

        logger.info(f"Local compute engine initialized on {self.hostname} ({self.platform})")
        logger.info(f"GPU: {'Available' if self.gpu_available else 'Not available'}")
        logger.info(f"Docker: {'Available' if self.docker_available else 'Not available'}")

    def get_resources(self) -> ComputeResources:
        """Get current compute resources"""
        try:
            # CPU
            cpu_count_physical = psutil.cpu_count(logical=False) or 0
            cpu_count_logical = psutil.cpu_count(logical=True) or 0
            cpu_freq = psutil.cpu_freq()
            cpu_usage = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)

            # Memory
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()

            # Network
            net_io = psutil.net_io_counters()
            net_if = psutil.net_if_addrs()

            # GPU
            gpu_info = self._get_gpu_info() if self.gpu_available else {
                'count': 0,
                'devices': [],
                'total_memory_gb': 0.0
            }

            # Docker
            docker_info = self._get_docker_info() if self.docker_available else {
                'version': None,
                'containers_running': 0
            }

            # System uptime
            uptime = (datetime.now() - self.boot_time).total_seconds() / 3600

            resources = ComputeResources(
                # CPU
                cpu_count_physical=cpu_count_physical,
                cpu_count_logical=cpu_count_logical,
                cpu_freq_current_mhz=cpu_freq.current if cpu_freq else 0,
                cpu_freq_max_mhz=cpu_freq.max if cpu_freq else 0,
                cpu_usage_percent=cpu_usage,
                cpu_per_core_usage=cpu_per_core,

                # GPU
                gpu_available=self.gpu_available,
                gpu_count=gpu_info['count'],
                gpu_devices=gpu_info['devices'],
                gpu_total_memory_gb=gpu_info['total_memory_gb'],

                # Memory
                memory_total_gb=memory.total / (1024 ** 3),
                memory_available_gb=memory.available / (1024 ** 3),
                memory_used_gb=memory.used / (1024 ** 3),
                memory_percent=memory.percent,
                swap_total_gb=swap.total / (1024 ** 3),
                swap_used_gb=swap.used / (1024 ** 3),

                # Disk
                disk_total_gb=disk.total / (1024 ** 3),
                disk_used_gb=disk.used / (1024 ** 3),
                disk_free_gb=disk.free / (1024 ** 3),
                disk_percent=disk.percent,
                disk_io_read_mb_s=(disk_io.read_bytes / (1024 ** 2)) if disk_io else 0,
                disk_io_write_mb_s=(disk_io.write_bytes / (1024 ** 2)) if disk_io else 0,

                # Network
                network_sent_mb=net_io.bytes_sent / (1024 ** 2),
                network_recv_mb=net_io.bytes_recv / (1024 ** 2),
                network_interfaces=list(net_if.keys()),

                # System
                platform=f"{self.platform} {platform.release()}",
                platform_version=platform.version(),
                hostname=self.hostname,
                boot_time=self.boot_time.isoformat(),
                uptime_hours=uptime,

                # Docker
                docker_available=self.docker_available,
                docker_version=docker_info['version'],
                containers_running=docker_info['containers_running'],

                # Timestamp
                measured_at=datetime.now().isoformat()
            )

            # Store in history
            self._add_to_history(resources)

            return resources

        except Exception as e:
            logger.error(f"Error getting resources: {e}")
            raise

    def _detect_gpu(self) -> bool:
        """Detect if GPU is available"""
        try:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("NVIDIA GPU detected")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try rocm-smi for AMD GPUs
        try:
            result = subprocess.run(
                ['rocm-smi', '--showproductname'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("AMD GPU detected")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False

    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information"""
        try:
            # Try NVIDIA first
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used,utilization.gpu',
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = []
                total_memory = 0

                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 5:
                            memory_total = float(parts[2])
                            devices.append({
                                'index': int(parts[0]),
                                'name': parts[1],
                                'memory_total_mb': memory_total,
                                'memory_used_mb': float(parts[3]),
                                'utilization_percent': float(parts[4])
                            })
                            total_memory += memory_total

                return {
                    'count': len(devices),
                    'devices': devices,
                    'total_memory_gb': total_memory / 1024
                }

        except Exception as e:
            logger.debug(f"Could not get GPU info: {e}")

        return {
            'count': 0,
            'devices': [],
            'total_memory_gb': 0.0
        }

    def _detect_docker(self) -> bool:
        """Detect if Docker is available"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _get_docker_info(self) -> Dict[str, Any]:
        """Get Docker information"""
        try:
            # Get version
            version_result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = version_result.stdout.strip() if version_result.returncode == 0 else None

            # Get running containers
            ps_result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True,
                text=True,
                timeout=5
            )
            containers = len(ps_result.stdout.strip().split('\n')) if ps_result.returncode == 0 else 0

            return {
                'version': version,
                'containers_running': containers
            }

        except Exception as e:
            logger.debug(f"Could not get Docker info: {e}")
            return {
                'version': None,
                'containers_running': 0
            }

    def _add_to_history(self, resources: ComputeResources):
        """Add resources to history"""
        self.metrics_history.append(resources)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

    def get_resource_trends(self, last_n: int = 10) -> Dict[str, Any]:
        """Get resource usage trends"""
        if not self.metrics_history:
            return {}

        recent = self.metrics_history[-last_n:]

        return {
            'cpu_avg': sum(r.cpu_usage_percent for r in recent) / len(recent),
            'cpu_max': max(r.cpu_usage_percent for r in recent),
            'cpu_min': min(r.cpu_usage_percent for r in recent),
            'memory_avg': sum(r.memory_percent for r in recent) / len(recent),
            'memory_max': max(r.memory_percent for r in recent),
            'memory_min': min(r.memory_percent for r in recent),
            'disk_avg': sum(r.disk_percent for r in recent) / len(recent),
            'samples': len(recent)
        }

    def get_dynamic_memory_allocation(
        self,
        overhead_percent: float = 40.0
    ) -> Dict[str, float]:
        """
        Calculate dynamic memory allocation with configurable overhead.

        After reserving overhead for system stability, returns how much
        memory can be safely allocated to workloads.

        Args:
            overhead_percent: Percentage to reserve for system (default 40%)
                             Example: 40% overhead means use max 60% of available memory

        Returns:
            Dict with memory allocation details
        """
        resources = self.get_resources()

        # Total available memory
        available_memory = resources.memory_available_gb

        # Calculate usable memory after overhead
        usable_percent = 100.0 - overhead_percent
        usable_memory = available_memory * (usable_percent / 100.0)

        # Reserved for system stability
        reserved_memory = available_memory * (overhead_percent / 100.0)

        return {
            'total_memory_gb': resources.memory_total_gb,
            'current_available_gb': available_memory,
            'overhead_percent': overhead_percent,
            'reserved_for_system_gb': reserved_memory,
            'usable_for_workload_gb': usable_memory,
            'current_usage_percent': resources.memory_percent
        }

    def can_handle_workload(
        self,
        required_cpu_cores: float,
        required_memory_gb: float,
        required_gpu: bool = False,
        cpu_threshold: float = 80.0,
        memory_overhead_percent: float = 40.0
    ) -> Dict[str, Any]:
        """
        Check if local machine can handle a workload with dynamic memory allocation.

        Args:
            required_cpu_cores: CPU cores needed
            required_memory_gb: Memory in GB needed
            required_gpu: Whether GPU is required
            cpu_threshold: Max CPU usage allowed (default 80%)
            memory_overhead_percent: Memory overhead to reserve (default 40%)
                                    This means only 60% of available memory is usable

        Returns:
            Dict with capacity check results
        """
        resources = self.get_resources()

        # Check CPU
        cpu_available_cores = resources.cpu_count_logical * (1 - resources.cpu_usage_percent / 100)
        cpu_ok = cpu_available_cores >= required_cpu_cores and resources.cpu_usage_percent < cpu_threshold

        # Dynamic Memory Check with Overhead
        memory_allocation = self.get_dynamic_memory_allocation(overhead_percent=memory_overhead_percent)
        usable_memory = memory_allocation['usable_for_workload_gb']
        memory_ok = usable_memory >= required_memory_gb

        # Check GPU
        gpu_ok = (not required_gpu) or (resources.gpu_available and resources.gpu_count > 0)

        can_handle = cpu_ok and memory_ok and gpu_ok

        return {
            'can_handle': can_handle,
            'cpu_ok': cpu_ok,
            'memory_ok': memory_ok,
            'gpu_ok': gpu_ok,
            'cpu_available_cores': cpu_available_cores,
            'memory_total_available_gb': memory_allocation['current_available_gb'],
            'memory_usable_after_overhead_gb': usable_memory,
            'memory_overhead_percent': memory_overhead_percent,
            'memory_reserved_for_system_gb': memory_allocation['reserved_for_system_gb'],
            'gpu_available': resources.gpu_available,
            'recommendation': self._get_recommendation(cpu_ok, memory_ok, gpu_ok, required_gpu)
        }

    def _get_recommendation(
        self,
        cpu_ok: bool,
        memory_ok: bool,
        gpu_ok: bool,
        gpu_required: bool
    ) -> str:
        """Get recommendation for workload execution"""
        if not cpu_ok:
            return "CPU usage too high - consider cloud execution or wait for resources"
        if not memory_ok:
            return "Insufficient memory - consider cloud execution or reduce workload"
        if gpu_required and not gpu_ok:
            return "GPU required but not available - use cloud GPU instances"
        if cpu_ok and memory_ok and gpu_ok:
            return "Local execution recommended - all resources available"
        return "Check resource requirements"

    def mount_volume(self, host_path: str, container_path: str) -> Dict[str, str]:
        """Mount local volume for container access"""
        return {
            'host_path': os.path.abspath(host_path),
            'container_path': container_path,
            'mount_string': f"{os.path.abspath(host_path)}:{container_path}"
        }

    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        resources = self.get_resources()

        return {
            'system': {
                'platform': resources.platform,
                'platform_version': resources.platform_version,
                'hostname': resources.hostname,
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            },
            'compute': {
                'cpu_physical_cores': resources.cpu_count_physical,
                'cpu_logical_cores': resources.cpu_count_logical,
                'cpu_frequency_mhz': resources.cpu_freq_current_mhz,
                'gpu_available': resources.gpu_available,
                'gpu_count': resources.gpu_count,
                'gpu_memory_gb': resources.gpu_total_memory_gb
            },
            'memory': {
                'total_gb': resources.memory_total_gb,
                'available_gb': resources.memory_available_gb,
                'percent_used': resources.memory_percent
            },
            'storage': {
                'total_gb': resources.disk_total_gb,
                'free_gb': resources.disk_free_gb,
                'percent_used': resources.disk_percent
            },
            'containers': {
                'docker_available': resources.docker_available,
                'docker_version': resources.docker_version,
                'running_containers': resources.containers_running
            },
            'uptime_hours': resources.uptime_hours,
            'boot_time': resources.boot_time
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert current resources to dictionary"""
        resources = self.get_resources()
        return asdict(resources)
