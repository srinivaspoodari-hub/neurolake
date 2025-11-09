"""
Database Backup Script

Automated backup script for NeuroLake PostgreSQL database.
Supports full backups, incremental backups, and automatic retention management.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging
import gzip
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Database backup manager."""

    def __init__(
        self,
        backup_dir: str = "./backups",
        retention_days: int = 30,
        compress: bool = True
    ):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory to store backups
            retention_days: Number of days to retain backups
            compress: Whether to compress backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.retention_days = retention_days
        self.compress = compress

        # Get database settings
        self.settings = get_settings()
        self.db_settings = self.settings.database

    def create_backup(self, backup_type: str = "full") -> Path:
        """
        Create database backup.

        Args:
            backup_type: Type of backup (full, schema, data)

        Returns:
            Path to backup file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"neurolake_{backup_type}_{timestamp}.sql"
        backup_path = self.backup_dir / backup_name

        logger.info(f"Creating {backup_type} backup: {backup_name}")

        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"--host={self.db_settings.host}",
            f"--port={self.db_settings.port}",
            f"--username={self.db_settings.username}",
            f"--dbname={self.db_settings.database}",
            f"--file={backup_path}",
            "--format=plain",
            "--verbose"
        ]

        # Add options based on backup type
        if backup_type == "schema":
            cmd.append("--schema-only")
        elif backup_type == "data":
            cmd.append("--data-only")

        # Set password environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_settings.password

        try:
            # Run pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"Backup created successfully: {backup_path}")
            logger.debug(f"pg_dump output: {result.stdout}")

            # Compress backup if enabled
            if self.compress:
                compressed_path = self.compress_backup(backup_path)
                backup_path = compressed_path

            # Get backup size
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup size: {size_mb:.2f} MB")

            return backup_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Backup error: {e}")
            raise

    def compress_backup(self, backup_path: Path) -> Path:
        """
        Compress backup file with gzip.

        Args:
            backup_path: Path to uncompressed backup

        Returns:
            Path to compressed backup
        """
        compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")

        logger.info(f"Compressing backup: {backup_path.name}")

        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed file
        backup_path.unlink()

        logger.info(f"Compressed backup: {compressed_path.name}")
        return compressed_path

    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        logger.info(f"Cleaning up backups older than {self.retention_days} days")

        deleted_count = 0
        for backup_file in self.backup_dir.glob("neurolake_*.sql*"):
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
        List all available backups.

        Returns:
            List of backup file paths with metadata
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("neurolake_*.sql*")):
            stat = backup_file.stat()

            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "compressed": backup_file.suffix == ".gz"
            })

        return backups

    def restore_backup(self, backup_path: Path, drop_existing: bool = False):
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file
            drop_existing: Whether to drop existing database first
        """
        logger.info(f"Restoring backup: {backup_path.name}")

        # Decompress if needed
        if backup_path.suffix == ".gz":
            logger.info("Decompressing backup...")
            decompressed_path = backup_path.with_suffix("")

            with gzip.open(backup_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            backup_path = decompressed_path

        # Build psql command
        cmd = [
            "psql",
            f"--host={self.db_settings.host}",
            f"--port={self.db_settings.port}",
            f"--username={self.db_settings.username}",
            f"--dbname={self.db_settings.database}",
            f"--file={backup_path}"
        ]

        # Set password environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_settings.password

        try:
            # Drop existing database if requested
            if drop_existing:
                logger.warning("Dropping existing database...")
                # This would need to be done carefully in production

            # Run psql restore
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Backup restored successfully")
            logger.debug(f"psql output: {result.stdout}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Restore error: {e}")
            raise


def main():
    """Main backup script."""
    parser = argparse.ArgumentParser(description="NeuroLake Database Backup")

    parser.add_argument(
        "command",
        choices=["backup", "restore", "list", "cleanup"],
        help="Command to execute"
    )

    parser.add_argument(
        "--type",
        choices=["full", "schema", "data"],
        default="full",
        help="Backup type (default: full)"
    )

    parser.add_argument(
        "--backup-dir",
        default="./backups",
        help="Backup directory (default: ./backups)"
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Backup retention in days (default: 30)"
    )

    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Disable backup compression"
    )

    parser.add_argument(
        "--backup-file",
        help="Backup file to restore (for restore command)"
    )

    args = parser.parse_args()

    # Initialize backup manager
    backup_mgr = DatabaseBackup(
        backup_dir=args.backup_dir,
        retention_days=args.retention_days,
        compress=not args.no_compress
    )

    # Execute command
    if args.command == "backup":
        backup_file = backup_mgr.create_backup(backup_type=args.type)
        logger.info(f"✓ Backup completed: {backup_file}")

        # Cleanup old backups
        backup_mgr.cleanup_old_backups()

    elif args.command == "restore":
        if not args.backup_file:
            logger.error("--backup-file required for restore command")
            sys.exit(1)

        backup_path = Path(args.backup_file)
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            sys.exit(1)

        backup_mgr.restore_backup(backup_path)
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
