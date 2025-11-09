"""
Backup Scheduler

Automated scheduler for running database and storage backups.
Can be run as a cron job or Windows scheduled task.
"""

import os
import sys
import argparse
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from neurolake.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupScheduler:
    """Automated backup scheduler."""

    def __init__(
        self,
        backup_dir: str = "./backups",
        enable_email: bool = False,
        email_recipients: list = None
    ):
        """
        Initialize backup scheduler.

        Args:
            backup_dir: Base backup directory
            enable_email: Whether to send email notifications
            email_recipients: List of email addresses for notifications
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.enable_email = enable_email
        self.email_recipients = email_recipients or []

        self.settings = get_settings()

        # Paths to backup scripts
        self.script_dir = Path(__file__).parent
        self.db_backup_script = self.script_dir / "backup_database.py"
        self.storage_backup_script = self.script_dir / "backup_storage.py"

    def run_database_backup(self) -> dict:
        """
        Run database backup.

        Returns:
            Backup result dict
        """
        logger.info("=" * 60)
        logger.info("Starting database backup")
        logger.info("=" * 60)

        start_time = datetime.utcnow()

        try:
            # Run backup script
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.db_backup_script),
                    "backup",
                    "--type", "full",
                    "--backup-dir", str(self.backup_dir / "database")
                ],
                capture_output=True,
                text=True,
                check=True
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info("Database backup completed successfully")
            logger.info(f"Duration: {duration:.2f} seconds")

            return {
                "success": True,
                "type": "database",
                "duration": duration,
                "output": result.stdout,
                "error": None
            }

        except subprocess.CalledProcessError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.error(f"Database backup failed: {e.stderr}")

            return {
                "success": False,
                "type": "database",
                "duration": duration,
                "output": e.stdout,
                "error": e.stderr
            }

    def run_storage_backup(self) -> dict:
        """
        Run storage backup.

        Returns:
            Backup result dict
        """
        logger.info("=" * 60)
        logger.info("Starting storage backup")
        logger.info("=" * 60)

        start_time = datetime.utcnow()

        try:
            # Run backup script
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.storage_backup_script),
                    "backup",
                    "--all",
                    "--backup-dir", str(self.backup_dir / "storage")
                ],
                capture_output=True,
                text=True,
                check=True
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info("Storage backup completed successfully")
            logger.info(f"Duration: {duration:.2f} seconds")

            return {
                "success": True,
                "type": "storage",
                "duration": duration,
                "output": result.stdout,
                "error": None
            }

        except subprocess.CalledProcessError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.error(f"Storage backup failed: {e.stderr}")

            return {
                "success": False,
                "type": "storage",
                "duration": duration,
                "output": e.stdout,
                "error": e.stderr
            }

    def run_all_backups(self) -> list:
        """
        Run all backups (database and storage).

        Returns:
            List of backup results
        """
        start_time = datetime.utcnow()

        logger.info("=" * 60)
        logger.info(f"Starting automated backups: {start_time.isoformat()}")
        logger.info("=" * 60)

        results = []

        # Run database backup
        db_result = self.run_database_backup()
        results.append(db_result)

        # Run storage backup
        storage_result = self.run_storage_backup()
        results.append(storage_result)

        # Calculate total duration
        total_duration = (datetime.utcnow() - start_time).total_seconds()

        # Log summary
        logger.info("=" * 60)
        logger.info("Backup Summary")
        logger.info("=" * 60)

        for result in results:
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            logger.info(f"{result['type'].upper()}: {status} ({result['duration']:.2f}s)")

        logger.info(f"Total duration: {total_duration:.2f} seconds")
        logger.info("=" * 60)

        # Send email notification if enabled
        if self.enable_email:
            self.send_email_notification(results, total_duration)

        return results

    def send_email_notification(self, results: list, total_duration: float):
        """
        Send email notification with backup results.

        Args:
            results: List of backup results
            total_duration: Total backup duration in seconds
        """
        try:
            # Build email content
            subject = "NeuroLake Backup Report"

            # Check if any backups failed
            failed = [r for r in results if not r["success"]]
            if failed:
                subject += " - ⚠ FAILURES DETECTED"

            # Build HTML body
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .success {{ color: green; }}
                    .failure {{ color: red; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h2>NeuroLake Backup Report</h2>
                <p><strong>Time:</strong> {datetime.utcnow().isoformat()}</p>
                <p><strong>Total Duration:</strong> {total_duration:.2f} seconds</p>

                <h3>Backup Results:</h3>
                <table>
                    <tr>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Duration</th>
                    </tr>
            """

            for result in results:
                status_class = "success" if result["success"] else "failure"
                status_text = "✓ SUCCESS" if result["success"] else "✗ FAILED"

                body += f"""
                    <tr>
                        <td>{result['type'].upper()}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{result['duration']:.2f}s</td>
                    </tr>
                """

            body += """
                </table>
            """

            # Add error details if any
            if failed:
                body += "<h3>Error Details:</h3>"
                for result in failed:
                    body += f"""
                        <h4>{result['type'].upper()} Error:</h4>
                        <pre>{result['error']}</pre>
                    """

            body += """
            </body>
            </html>
            """

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = "noreply@neurolake.com"
            msg['To'] = ", ".join(self.email_recipients)

            # Attach HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)

            # Send email (configure SMTP settings)
            # This is a placeholder - configure actual SMTP settings
            logger.info("Email notification would be sent to: " + ", ".join(self.email_recipients))
            logger.debug(f"Email subject: {subject}")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")


def main():
    """Main scheduler script."""
    parser = argparse.ArgumentParser(description="NeuroLake Backup Scheduler")

    parser.add_argument(
        "command",
        choices=["run", "database", "storage"],
        help="Command to execute (run=all backups)"
    )

    parser.add_argument(
        "--backup-dir",
        default="./backups",
        help="Base backup directory (default: ./backups)"
    )

    parser.add_argument(
        "--email",
        action="store_true",
        help="Enable email notifications"
    )

    parser.add_argument(
        "--recipients",
        nargs="+",
        help="Email recipients for notifications"
    )

    args = parser.parse_args()

    # Initialize scheduler
    scheduler = BackupScheduler(
        backup_dir=args.backup_dir,
        enable_email=args.email,
        email_recipients=args.recipients
    )

    # Execute command
    if args.command == "run":
        results = scheduler.run_all_backups()

        # Exit with error code if any backup failed
        if any(not r["success"] for r in results):
            sys.exit(1)

    elif args.command == "database":
        result = scheduler.run_database_backup()

        if not result["success"]:
            sys.exit(1)

    elif args.command == "storage":
        result = scheduler.run_storage_backup()

        if not result["success"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
