"""
Distributed Compute Engine

Provides integration with distributed computing frameworks:
- Ray (distributed Python)
- Dask (parallel computing)
- Apache Spark (big data processing)
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class DistributedFramework(str, Enum):
    """Supported distributed frameworks"""
    RAY = "ray"
    DASK = "dask"
    SPARK = "spark"


class DistributedComputeEngine:
    """
    Distributed Compute Engine

    Manages distributed computing frameworks for parallel/distributed workloads.
    """

    def __init__(self):
        """Initialize distributed compute engine"""
        self.frameworks_available = {
            DistributedFramework.RAY: self._check_ray(),
            DistributedFramework.DASK: self._check_dask(),
            DistributedFramework.SPARK: self._check_spark(),
        }

        self.active_clusters: Dict[DistributedFramework, Any] = {}

        logger.info(f"Distributed compute engine initialized")
        logger.info(f"Available frameworks: {[f.value for f, avail in self.frameworks_available.items() if avail]}")

    def _check_ray(self) -> bool:
        """Check if Ray is available"""
        try:
            import ray
            return True
        except ImportError:
            logger.debug("Ray not available")
            return False

    def _check_dask(self) -> bool:
        """Check if Dask is available"""
        try:
            import dask
            import dask.distributed
            return True
        except ImportError:
            logger.debug("Dask not available")
            return False

    def _check_spark(self) -> bool:
        """Check if Spark is available"""
        try:
            import pyspark
            return True
        except ImportError:
            logger.debug("Spark not available")
            return False

    def initialize_ray(
        self,
        num_cpus: Optional[int] = None,
        num_gpus: Optional[int] = None,
        memory: Optional[int] = None,
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize Ray cluster

        Args:
            num_cpus: Number of CPUs to allocate
            num_gpus: Number of GPUs to allocate
            memory: Memory in bytes
            address: Ray cluster address (for connecting to existing cluster)

        Returns:
            Cluster info
        """
        if not self.frameworks_available[DistributedFramework.RAY]:
            raise RuntimeError("Ray is not installed")

        try:
            import ray

            if address:
                # Connect to existing cluster
                ray.init(address=address)
                logger.info(f"Connected to Ray cluster at {address}")
            else:
                # Start local cluster
                ray.init(
                    num_cpus=num_cpus,
                    num_gpus=num_gpus,
                    _memory=memory,
                    ignore_reinit_error=True
                )
                logger.info(f"Started local Ray cluster")

            self.active_clusters[DistributedFramework.RAY] = ray

            cluster_resources = ray.cluster_resources()

            return {
                'framework': 'ray',
                'status': 'initialized',
                'cpus': cluster_resources.get('CPU', 0),
                'gpus': cluster_resources.get('GPU', 0),
                'memory_bytes': cluster_resources.get('memory', 0),
                'nodes': len(ray.nodes()) if hasattr(ray, 'nodes') else 1
            }

        except Exception as e:
            logger.error(f"Failed to initialize Ray: {e}")
            raise

    def initialize_dask(
        self,
        n_workers: int = 4,
        threads_per_worker: int = 2,
        memory_limit: str = '4GB',
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize Dask cluster

        Args:
            n_workers: Number of workers
            threads_per_worker: Threads per worker
            memory_limit: Memory limit per worker
            address: Dask scheduler address (for connecting to existing cluster)

        Returns:
            Cluster info
        """
        if not self.frameworks_available[DistributedFramework.DASK]:
            raise RuntimeError("Dask is not installed")

        try:
            from dask.distributed import Client, LocalCluster

            if address:
                # Connect to existing cluster
                client = Client(address)
                logger.info(f"Connected to Dask cluster at {address}")
            else:
                # Start local cluster
                cluster = LocalCluster(
                    n_workers=n_workers,
                    threads_per_worker=threads_per_worker,
                    memory_limit=memory_limit
                )
                client = Client(cluster)
                logger.info(f"Started local Dask cluster with {n_workers} workers")

            self.active_clusters[DistributedFramework.DASK] = client

            return {
                'framework': 'dask',
                'status': 'initialized',
                'scheduler': str(client.scheduler),
                'workers': len(client.scheduler_info()['workers']),
                'total_cores': sum(w['nthreads'] for w in client.scheduler_info()['workers'].values()),
                'dashboard_link': client.dashboard_link
            }

        except Exception as e:
            logger.error(f"Failed to initialize Dask: {e}")
            raise

    def initialize_spark(
        self,
        app_name: str = "NeuroLake",
        master: str = "local[*]",
        config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Initialize Spark session

        Args:
            app_name: Spark application name
            master: Spark master URL
            config: Spark configuration options

        Returns:
            Session info
        """
        if not self.frameworks_available[DistributedFramework.SPARK]:
            raise RuntimeError("Spark is not installed")

        try:
            from pyspark.sql import SparkSession

            builder = SparkSession.builder.appName(app_name).master(master)

            # Add configuration
            if config:
                for key, value in config.items():
                    builder = builder.config(key, value)

            spark = builder.getOrCreate()

            self.active_clusters[DistributedFramework.SPARK] = spark

            sc = spark.sparkContext

            logger.info(f"Spark session initialized: {app_name}")

            return {
                'framework': 'spark',
                'status': 'initialized',
                'app_name': app_name,
                'master': master,
                'spark_version': spark.version,
                'default_parallelism': sc.defaultParallelism,
                'web_ui': sc.uiWebUrl
            }

        except Exception as e:
            logger.error(f"Failed to initialize Spark: {e}")
            raise

    def submit_ray_task(
        self,
        func: callable,
        *args,
        **kwargs
    ) -> Any:
        """Submit task to Ray"""
        if DistributedFramework.RAY not in self.active_clusters:
            raise RuntimeError("Ray cluster not initialized")

        import ray

        @ray.remote
        def ray_task(f, *a, **kw):
            return f(*a, **kw)

        future = ray_task.remote(func, *args, **kwargs)
        return ray.get(future)

    def submit_dask_task(
        self,
        func: callable,
        *args,
        **kwargs
    ) -> Any:
        """Submit task to Dask"""
        if DistributedFramework.DASK not in self.active_clusters:
            raise RuntimeError("Dask cluster not initialized")

        client = self.active_clusters[DistributedFramework.DASK]
        future = client.submit(func, *args, **kwargs)
        return future.result()

    def submit_spark_job(
        self,
        data_path: str,
        transformation_func: callable
    ) -> Any:
        """Submit Spark job"""
        if DistributedFramework.SPARK not in self.active_clusters:
            raise RuntimeError("Spark session not initialized")

        spark = self.active_clusters[DistributedFramework.SPARK]

        # Load data
        df = spark.read.parquet(data_path)

        # Apply transformation
        result = transformation_func(df)

        return result

    def shutdown_framework(self, framework: DistributedFramework):
        """Shutdown a distributed framework"""
        if framework not in self.active_clusters:
            logger.warning(f"{framework.value} cluster not active")
            return

        try:
            if framework == DistributedFramework.RAY:
                import ray
                ray.shutdown()

            elif framework == DistributedFramework.DASK:
                client = self.active_clusters[framework]
                client.close()

            elif framework == DistributedFramework.SPARK:
                spark = self.active_clusters[framework]
                spark.stop()

            del self.active_clusters[framework]
            logger.info(f"{framework.value} cluster shutdown")

        except Exception as e:
            logger.error(f"Error shutting down {framework.value}: {e}")

    def get_cluster_status(
        self,
        framework: DistributedFramework
    ) -> Dict[str, Any]:
        """Get cluster status"""
        if framework not in self.active_clusters:
            return {
                'framework': framework.value,
                'status': 'not_initialized'
            }

        try:
            if framework == DistributedFramework.RAY:
                import ray
                resources = ray.cluster_resources()
                return {
                    'framework': 'ray',
                    'status': 'active',
                    'resources': resources,
                    'available': ray.available_resources()
                }

            elif framework == DistributedFramework.DASK:
                client = self.active_clusters[framework]
                return {
                    'framework': 'dask',
                    'status': 'active',
                    'scheduler_info': client.scheduler_info(),
                    'dashboard': client.dashboard_link
                }

            elif framework == DistributedFramework.SPARK:
                spark = self.active_clusters[framework]
                sc = spark.sparkContext
                return {
                    'framework': 'spark',
                    'status': 'active',
                    'application_id': sc.applicationId,
                    'web_ui': sc.uiWebUrl,
                    'default_parallelism': sc.defaultParallelism
                }

        except Exception as e:
            logger.error(f"Error getting {framework.value} status: {e}")
            return {
                'framework': framework.value,
                'status': 'error',
                'error': str(e)
            }

    def get_active_frameworks(self) -> List[str]:
        """Get list of active frameworks"""
        return [f.value for f in self.active_clusters.keys()]

    def get_available_frameworks(self) -> Dict[str, bool]:
        """Get availability status of all frameworks"""
        return {f.value: avail for f, avail in self.frameworks_available.items()}
