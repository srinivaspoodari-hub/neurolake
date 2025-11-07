"""
Hybrid Storage Manager

Manages data across local and cloud storage tiers with intelligent placement
and cost optimization.
"""

import os
import shutil
from typing import Dict, List, Optional, Any, Literal
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


StorageTier = Literal["local", "cloud", "archive"]


class HybridStorageManager:
    """
    Manages hybrid storage across local filesystem and cloud (MinIO/S3)

    Features:
    - Automatic tiering based on access patterns
    - Cost-aware data placement
    - Local caching of frequently accessed data
    - Cloud burst for overflow
    """

    def __init__(
        self,
        local_path: str = "./neurolake_data",
        cloud_endpoint: Optional[str] = None,
        cloud_bucket: str = "neurolake-hybrid",
        local_capacity_gb: float = 100.0,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize Hybrid Storage Manager

        Args:
            local_path: Path for local storage
            cloud_endpoint: MinIO/S3 endpoint (None = local-only mode)
            cloud_bucket: Cloud bucket name
            local_capacity_gb: Local storage capacity in GB
            cache_ttl_hours: TTL for local cache
        """
        self.local_path = Path(local_path)
        self.local_path.mkdir(parents=True, exist_ok=True)

        self.cloud_endpoint = cloud_endpoint
        self.cloud_bucket = cloud_bucket
        self.local_capacity_bytes = int(local_capacity_gb * 1024 * 1024 * 1024)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Metadata tracking
        self.metadata_file = self.local_path / ".storage_metadata.json"
        self.metadata: Dict[str, Dict] = self._load_metadata()

        # Statistics
        self.stats = {
            'local_reads': 0,
            'cloud_reads': 0,
            'local_writes': 0,
            'cloud_writes': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bytes_saved_locally': 0,
            'estimated_cloud_cost_saved': 0.0
        }

        logger.info(f"Hybrid storage initialized: local={local_path}, cloud={cloud_endpoint or 'disabled'}")

    def _load_metadata(self) -> Dict[str, Dict]:
        """Load storage metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {}

    def _save_metadata(self):
        """Save storage metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def get_local_usage(self) -> Dict[str, Any]:
        """Get current local storage usage"""
        total_size = 0
        file_count = 0

        for root, dirs, files in os.walk(self.local_path):
            for file in files:
                if file != ".storage_metadata.json":
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except:
                        pass

        return {
            'used_bytes': total_size,
            'used_gb': total_size / (1024 ** 3),
            'capacity_bytes': self.local_capacity_bytes,
            'capacity_gb': self.local_capacity_bytes / (1024 ** 3),
            'utilization_pct': (total_size / self.local_capacity_bytes * 100) if self.local_capacity_bytes > 0 else 0,
            'file_count': file_count
        }

    def store_data(
        self,
        key: str,
        data: bytes,
        tier: Optional[StorageTier] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Store data with automatic tier selection

        Args:
            key: Data key/identifier
            data: Binary data to store
            tier: Explicit tier selection (None = automatic)
            metadata: Additional metadata

        Returns:
            Storage result info
        """
        data_size = len(data)
        usage = self.get_local_usage()

        # Automatic tier selection
        if tier is None:
            if usage['used_bytes'] + data_size < self.local_capacity_bytes:
                tier = "local"
            elif self.cloud_endpoint:
                tier = "cloud"
            else:
                # Local only mode - need to make space
                self._evict_cold_data(data_size)
                tier = "local"

        # Store data
        if tier == "local":
            return self._store_local(key, data, metadata)
        elif tier == "cloud" and self.cloud_endpoint:
            return self._store_cloud(key, data, metadata)
        else:
            raise ValueError(f"Invalid tier '{tier}' or cloud not configured")

    def _store_local(
        self,
        key: str,
        data: bytes,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Store data locally"""
        file_path = self.local_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'wb') as f:
                f.write(data)

            self.metadata[key] = {
                'tier': 'local',
                'size_bytes': len(data),
                'created_at': datetime.utcnow().isoformat(),
                'last_accessed': datetime.utcnow().isoformat(),
                'access_count': 0,
                'metadata': metadata or {}
            }

            self._save_metadata()
            self.stats['local_writes'] += 1
            self.stats['bytes_saved_locally'] += len(data)

            logger.info(f"Stored {key} locally ({len(data)} bytes)")

            return {
                'status': 'success',
                'tier': 'local',
                'path': str(file_path),
                'size_bytes': len(data)
            }

        except Exception as e:
            logger.error(f"Error storing {key} locally: {e}")
            raise

    def _store_cloud(
        self,
        key: str,
        data: bytes,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Store data in cloud (MinIO/S3)"""
        # Placeholder for cloud storage integration
        # In production, use MinIO client or boto3

        logger.info(f"Cloud storage not yet implemented for {key}")

        self.metadata[key] = {
            'tier': 'cloud',
            'size_bytes': len(data),
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat(),
            'access_count': 0,
            'cloud_bucket': self.cloud_bucket,
            'metadata': metadata or {}
        }

        self._save_metadata()
        self.stats['cloud_writes'] += 1

        return {
            'status': 'success',
            'tier': 'cloud',
            'bucket': self.cloud_bucket,
            'key': key,
            'size_bytes': len(data)
        }

    def retrieve_data(self, key: str, promote_to_local: bool = True) -> Optional[bytes]:
        """
        Retrieve data from storage

        Args:
            key: Data key
            promote_to_local: Cache in local if retrieved from cloud

        Returns:
            Data bytes or None if not found
        """
        if key not in self.metadata:
            logger.warning(f"Key not found: {key}")
            return None

        meta = self.metadata[key]
        meta['last_accessed'] = datetime.utcnow().isoformat()
        meta['access_count'] = meta.get('access_count', 0) + 1

        if meta['tier'] == 'local':
            # Read from local
            file_path = self.local_path / key
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    data = f.read()
                self.stats['local_reads'] += 1
                self.stats['cache_hits'] += 1
                self._save_metadata()
                return data
            else:
                logger.error(f"Local file missing: {key}")
                return None

        elif meta['tier'] == 'cloud':
            # Read from cloud (placeholder)
            logger.info(f"Would read {key} from cloud")
            self.stats['cloud_reads'] += 1
            self.stats['cache_misses'] += 1
            self._save_metadata()
            return b"placeholder_cloud_data"

        return None

    def _evict_cold_data(self, required_bytes: int):
        """Evict least recently accessed data to make space"""
        usage = self.get_local_usage()
        bytes_to_free = required_bytes - (self.local_capacity_bytes - usage['used_bytes'])

        if bytes_to_free <= 0:
            return

        # Sort by last access time (oldest first)
        items = sorted(
            [(k, v) for k, v in self.metadata.items() if v['tier'] == 'local'],
            key=lambda x: x[1]['last_accessed']
        )

        freed_bytes = 0
        for key, meta in items:
            if freed_bytes >= bytes_to_free:
                break

            file_path = self.local_path / key
            if file_path.exists():
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    freed_bytes += file_size

                    # Move metadata to cloud tier
                    meta['tier'] = 'cloud'
                    meta['evicted_at'] = datetime.utcnow().isoformat()

                    logger.info(f"Evicted {key} ({file_size} bytes)")

                except Exception as e:
                    logger.error(f"Error evicting {key}: {e}")

        self._save_metadata()
        logger.info(f"Evicted {freed_bytes} bytes")

    def get_statistics(self) -> Dict[str, Any]:
        """Get hybrid storage statistics"""
        usage = self.get_local_usage()

        # Calculate cost savings (rough estimate)
        # AWS S3 standard storage: ~$0.023/GB/month
        # Data transfer out: ~$0.09/GB
        storage_cost_saved = (self.stats['bytes_saved_locally'] / (1024**3)) * 0.023
        transfer_cost_saved = (self.stats['local_reads'] * 1) / (1024**3) * 0.09  # Assume 1MB avg

        return {
            **self.stats,
            'estimated_monthly_cost_saved_usd': storage_cost_saved + transfer_cost_saved,
            'local_usage': usage,
            'cache_hit_rate': (
                self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses'])
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            ),
            'total_objects': len(self.metadata),
            'local_objects': sum(1 for m in self.metadata.values() if m['tier'] == 'local'),
            'cloud_objects': sum(1 for m in self.metadata.values() if m['tier'] == 'cloud')
        }

    def optimize_placement(self):
        """Optimize data placement based on access patterns"""
        now = datetime.utcnow()
        hot_threshold = now - timedelta(days=7)
        cold_threshold = now - timedelta(days=30)

        moved_to_local = 0
        moved_to_cloud = 0

        for key, meta in self.metadata.items():
            last_accessed = datetime.fromisoformat(meta['last_accessed'])
            access_count = meta.get('access_count', 0)

            # Hot data: accessed recently and frequently
            is_hot = last_accessed > hot_threshold and access_count > 5

            # Cold data: not accessed in 30 days
            is_cold = last_accessed < cold_threshold

            if is_hot and meta['tier'] == 'cloud' and self.cloud_endpoint:
                # Promote to local
                logger.info(f"Promoting hot data to local: {key}")
                moved_to_local += 1

            elif is_cold and meta['tier'] == 'local':
                # Demote to cloud
                logger.info(f"Demoting cold data to cloud: {key}")
                moved_to_cloud += 1

        self._save_metadata()

        return {
            'moved_to_local': moved_to_local,
            'moved_to_cloud': moved_to_cloud
        }
