"""
Storage Backup Script

Automated backup script for NeuroLake object storage (MinIO/S3).
Backs up NCF files, metadata, and user data.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
import tarfile
import gzip

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StorageBackup:
    """Object storage backup manager."""

    def __init__(
        self,
        backup_dir: str = "./backups/storage",
        retention_days: int = 30
    ):
        """
        Initialize storage backup manager.

        Args:
            backup_dir: Directory to store backups
            retention_days: Number of days to retain backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.retention_days = retention_days

        # Get settings
        self.settings = get_settings()
        self.storage_settings = self.settings.storage

        # Initialize MinIO client
        self.minio_client = None
        self._init_minio()

    def _init_minio(self):
        """Initialize MinIO client."""
        try:
            from minio import Minio

            self.minio_client = Minio(
                self.storage_settings.endpoint,
                access_key=self.storage_settings.access_key,
                secret_key=self.storage_settings.secret_key,
                secure=self.storage_settings.secure
            )

            logger.info(f"Connected to MinIO: {self.storage_settings.endpoint}")

        except ImportError:
            logger.warning("MinIO client not installed. Install with: pip install minio")
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")

    def backup_bucket(self, bucket_name: str) -> Path:
        """
        Backup entire bucket to tarball.

        Args:
            bucket_name: Name of bucket to backup

        Returns:
            Path to backup archive
        """
        if not self.minio_client:
            raise RuntimeError("MinIO client not initialized")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"storage_{bucket_name}_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name

        logger.info(f"Backing up bucket: {bucket_name}")

        # Create temporary directory for downloads
        temp_dir = self.backup_dir / f"temp_{timestamp}"
        temp_dir.mkdir(exist_ok=True)

        try:
            # List all objects in bucket
            objects = self.minio_client.list_objects(bucket_name, recursive=True)

            object_count = 0
            total_size = 0

            for obj in objects:
                object_path = temp_dir / obj.object_name
                object_path.parent.mkdir(parents=True, exist_ok=True)

                # Download object
                logger.debug(f"Downloading: {obj.object_name}")
                self.minio_client.fget_object(
                    bucket_name,
                    obj.object_name,
                    str(object_path)
                )

                object_count += 1
                total_size += obj.size

            logger.info(f"Downloaded {object_count} objects ({total_size / (1024*1024):.2f} MB)")

            # Create tarball
            logger.info(f"Creating archive: {backup_name}")

            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(temp_dir, arcname=bucket_name)

            # Get backup size
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup created: {backup_path.name} ({backup_size_mb:.2f} MB)")

            return backup_path

        finally:
            # Cleanup temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def backup_all_buckets(self) -> list:
        """
        Backup all buckets.

        Returns:
            List of backup file paths
        """
        if not self.minio_client:
            raise RuntimeError("MinIO client not initialized")

        buckets = [
            self.storage_settings.data_bucket,
            self.storage_settings.temp_bucket,
            self.storage_settings.archive_bucket
        ]

        backup_files = []

        for bucket in buckets:
            try:
                # Check if bucket exists
                if not self.minio_client.bucket_exists(bucket):
                    logger.warning(f"Bucket does not exist: {bucket}")
                    continue

                backup_file = self.backup_bucket(bucket)
                backup_files.append(backup_file)

            except Exception as e:
                logger.error(f"Failed to backup bucket {bucket}: {e}")

        return backup_files

    def restore_bucket(self, backup_path: Path, bucket_name: str, overwrite: bool = False):
        """
        Restore bucket from backup archive.

        Args:
            backup_path: Path to backup archive
            bucket_name: Name of bucket to restore to
            overwrite: Whether to overwrite existing objects
        """
        if not self.minio_client:
            raise RuntimeError("MinIO client not initialized")

        logger.info(f"Restoring bucket from: {backup_path.name}")

        # Create temporary directory for extraction
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        temp_dir = self.backup_dir / f"restore_{timestamp}"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Extract tarball
            logger.info("Extracting archive...")

            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Get extracted bucket directory
            bucket_dir = temp_dir / bucket_name

            if not bucket_dir.exists():
                # Try to find the bucket directory
                subdirs = list(temp_dir.iterdir())
                if subdirs:
                    bucket_dir = subdirs[0]
                else:
                    raise ValueError("No data found in backup archive")

            # Ensure bucket exists
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")

            # Upload all files
            uploaded_count = 0

            for file_path in bucket_dir.rglob("*"):
                if file_path.is_file():
                    # Get relative path for object name
                    object_name = str(file_path.relative_to(bucket_dir))

                    # Check if object exists
                    if not overwrite:
                        try:
                            self.minio_client.stat_object(bucket_name, object_name)
                            logger.debug(f"Skipping existing object: {object_name}")
                            continue
                        except:
                            pass  # Object doesn't exist, upload it

                    # Upload file
                    logger.debug(f"Uploading: {object_name}")
                    self.minio_client.fput_object(
                        bucket_name,
                        object_name,
                        str(file_path)
                    )

                    uploaded_count += 1

            logger.info(f"Restored {uploaded_count} objects to bucket: {bucket_name}")

        finally:
            # Cleanup temp directory
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        logger.info(f"Cleaning up backups older than {self.retention_days} days")

        deleted_count = 0
        for backup_file in self.backup_dir.glob("storage_*.tar.gz"):
            # Extract timestamp from filename
            try:
                parts = backup_file.stem.split("_")
                if len(parts) >= 3:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    if backup_date < cutoff_date:
                        logger.info(f"Deleting old backup: {backup_file.name}")
                        backup_file.unlink()
                        deleted_count += 1

            except Exception as e:
                logger.warning(f"Could not parse backup file {backup_file.name}: {e}")

        logger.info(f"Deleted {deleted_count} old backup(s)")

    def list_backups(self) -> list:
        """
        List all available storage backups.

        Returns:
            List of backup file paths with metadata
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("storage_*.tar.gz")):
            stat = backup_file.stat()

            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })

        return backups


def main():
    """Main storage backup script."""
    parser = argparse.ArgumentParser(description="NeuroLake Storage Backup")

    parser.add_argument(
        "command",
        choices=["backup", "restore", "list", "cleanup"],
        help="Command to execute"
    )

    parser.add_argument(
        "--bucket",
        help="Specific bucket to backup/restore"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Backup all buckets"
    )

    parser.add_argument(
        "--backup-dir",
        default="./backups/storage",
        help="Backup directory (default: ./backups/storage)"
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Backup retention in days (default: 30)"
    )

    parser.add_argument(
        "--backup-file",
        help="Backup file to restore (for restore command)"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing objects during restore"
    )

    args = parser.parse_args()

    # Initialize backup manager
    backup_mgr = StorageBackup(
        backup_dir=args.backup_dir,
        retention_days=args.retention_days
    )

    # Execute command
    if args.command == "backup":
        if args.all:
            backup_files = backup_mgr.backup_all_buckets()
            logger.info(f"✓ Backup completed: {len(backup_files)} bucket(s)")
        elif args.bucket:
            backup_file = backup_mgr.backup_bucket(args.bucket)
            logger.info(f"✓ Backup completed: {backup_file}")
        else:
            logger.error("Specify --bucket or --all")
            sys.exit(1)

        # Cleanup old backups
        backup_mgr.cleanup_old_backups()

    elif args.command == "restore":
        if not args.backup_file:
            logger.error("--backup-file required for restore command")
            sys.exit(1)

        if not args.bucket:
            logger.error("--bucket required for restore command")
            sys.exit(1)

        backup_path = Path(args.backup_file)
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            sys.exit(1)

        backup_mgr.restore_bucket(backup_path, args.bucket, overwrite=args.overwrite)
        logger.info("✓ Restore completed")

    elif args.command == "list":
        backups = backup_mgr.list_backups()

        if not backups:
            logger.info("No backups found")
        else:
            logger.info(f"Found {len(backups)} backup(s):")
            for backup in backups:
                logger.info(
                    f"  - {backup['name']} "
                    f"({backup['size_mb']:.2f} MB, {backup['created']})"
                )

    elif args.command == "cleanup":
        backup_mgr.cleanup_old_backups()
        logger.info("✓ Cleanup completed")


if __name__ == "__main__":
    main()
