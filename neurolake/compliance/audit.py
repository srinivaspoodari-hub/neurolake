"""
Audit Logger

Comprehensive audit logging for data access and compliance.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    DATA_ACCESS = "data_access"
    DATA_QUERY = "data_query"
    DATA_MODIFICATION = "data_modification"
    DATA_EXPORT = "data_export"
    PII_DETECTION = "pii_detection"
    POLICY_VIOLATION = "policy_violation"
    MASKING_APPLIED = "masking_applied"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"


class AuditLevel(Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """An audit log event."""
    event_type: AuditEventType
    level: AuditLevel
    message: str
    user: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    status: str = "success"
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["level"] = self.level.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Comprehensive audit logger for compliance.

    Example:
        logger = AuditLogger(log_file="audit.log")

        # Log data access
        logger.log_access(
            resource="users_table",
            action="SELECT",
            user="john@example.com"
        )

        # Log PII detection
        logger.log_pii_detection(
            text="Found email",
            pii_count=1,
            user="analyst@example.com"
        )

        # Log policy violation
        logger.log_violation(
            policy_name="no_pii",
            severity="critical",
            details="PII detected in query"
        )

        # Get recent events
        events = logger.get_events(limit=10)
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        max_events: int = 10000,
        auto_flush: bool = True
    ):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
            max_events: Maximum events to keep in memory
            auto_flush: Automatically flush to file
        """
        self.log_file = Path(log_file) if log_file else None
        self.max_events = max_events
        self.auto_flush = auto_flush
        self.events: List[AuditEvent] = []

        # Create log file if specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        message: str,
        level: str = "info",
        user: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log a general audit event.

        Args:
            event_type: Type of event
            message: Event message
            level: Severity level
            user: User identifier
            resource: Resource being accessed
            action: Action performed
            status: Event status
            metadata: Additional metadata

        Returns:
            Created audit event
        """
        event = AuditEvent(
            event_type=AuditEventType[event_type.upper()],
            level=AuditLevel[level.upper()],
            message=message,
            user=user,
            resource=resource,
            action=action,
            status=status,
            metadata=metadata or {}
        )

        self._record_event(event)
        return event

    def log_access(
        self,
        resource: str,
        action: str,
        user: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log data access event.

        Args:
            resource: Resource being accessed
            action: Action performed (SELECT, INSERT, etc.)
            user: User identifier
            status: Access status
            metadata: Additional metadata

        Returns:
            Created audit event
        """
        message = f"User {user or 'anonymous'} performed {action} on {resource}"

        return self.log_event(
            event_type="data_access",
            message=message,
            level="info",
            user=user,
            resource=resource,
            action=action,
            status=status,
            metadata=metadata
        )

    def log_query(
        self,
        query: str,
        user: Optional[str] = None,
        table: Optional[str] = None,
        rows_returned: Optional[int] = None,
        execution_time: Optional[float] = None
    ) -> AuditEvent:
        """
        Log query execution.

        Args:
            query: SQL query
            user: User executing query
            table: Table being queried
            rows_returned: Number of rows returned
            execution_time: Query execution time

        Returns:
            Created audit event
        """
        metadata = {
            "query": query,
            "rows_returned": rows_returned,
            "execution_time_ms": execution_time
        }

        message = f"Query executed by {user or 'anonymous'}"
        if table:
            message += f" on {table}"

        return self.log_event(
            event_type="data_query",
            message=message,
            level="info",
            user=user,
            resource=table,
            action="QUERY",
            metadata=metadata
        )

    def log_pii_detection(
        self,
        text: str,
        pii_count: int,
        pii_types: Optional[List[str]] = None,
        user: Optional[str] = None
    ) -> AuditEvent:
        """
        Log PII detection event.

        Args:
            text: Text analyzed (truncated)
            pii_count: Number of PII entities found
            pii_types: Types of PII detected
            user: User who triggered detection

        Returns:
            Created audit event
        """
        metadata = {
            "pii_count": pii_count,
            "pii_types": pii_types or [],
            "text_preview": text[:100] if text else None
        }

        level = "warning" if pii_count > 0 else "info"
        message = f"PII detection: found {pii_count} entities"

        return self.log_event(
            event_type="pii_detection",
            message=message,
            level=level,
            user=user,
            metadata=metadata
        )

    def log_violation(
        self,
        policy_name: str,
        severity: str,
        details: str,
        user: Optional[str] = None,
        resource: Optional[str] = None
    ) -> AuditEvent:
        """
        Log policy violation.

        Args:
            policy_name: Name of violated policy
            severity: Violation severity
            details: Violation details
            user: User who triggered violation
            resource: Resource involved

        Returns:
            Created audit event
        """
        metadata = {
            "policy_name": policy_name,
            "severity": severity,
            "details": details
        }

        message = f"Policy violation: {policy_name} - {details}"

        return self.log_event(
            event_type="policy_violation",
            message=message,
            level=severity,
            user=user,
            resource=resource,
            status="violation",
            metadata=metadata
        )

    def log_masking(
        self,
        strategy: str,
        entity_count: int,
        user: Optional[str] = None,
        resource: Optional[str] = None
    ) -> AuditEvent:
        """
        Log data masking event.

        Args:
            strategy: Masking strategy used
            entity_count: Number of entities masked
            user: User who applied masking
            resource: Resource being masked

        Returns:
            Created audit event
        """
        metadata = {
            "strategy": strategy,
            "entity_count": entity_count
        }

        message = f"Masked {entity_count} entities using {strategy} strategy"

        return self.log_event(
            event_type="masking_applied",
            message=message,
            level="info",
            user=user,
            resource=resource,
            action="MASK",
            metadata=metadata
        )

    def log_export(
        self,
        destination: str,
        record_count: int,
        user: Optional[str] = None,
        format: Optional[str] = None
    ) -> AuditEvent:
        """
        Log data export event.

        Args:
            destination: Export destination
            record_count: Number of records exported
            user: User performing export
            format: Export format

        Returns:
            Created audit event
        """
        metadata = {
            "destination": destination,
            "record_count": record_count,
            "format": format
        }

        message = f"Exported {record_count} records to {destination}"

        return self.log_event(
            event_type="data_export",
            message=message,
            level="warning",
            user=user,
            resource=destination,
            action="EXPORT",
            metadata=metadata
        )

    def _record_event(self, event: AuditEvent):
        """Record event to memory and file."""
        # Add to memory
        self.events.append(event)

        # Trim if exceeds max
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        # Log to Python logger
        logger.log(
            self._get_log_level(event.level),
            f"[AUDIT] {event.message}",
            extra={"audit_event": event.to_dict()}
        )

        # Write to file if configured
        if self.log_file and self.auto_flush:
            self._write_to_file(event)

    def _write_to_file(self, event: AuditEvent):
        """Write event to audit log file."""
        try:
            with open(self.log_file, 'a') as f:
                f.write(event.to_json() + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _get_log_level(self, level: AuditLevel) -> int:
        """Convert audit level to logging level."""
        mapping = {
            AuditLevel.DEBUG: logging.DEBUG,
            AuditLevel.INFO: logging.INFO,
            AuditLevel.WARNING: logging.WARNING,
            AuditLevel.ERROR: logging.ERROR,
            AuditLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO)

    def get_events(
        self,
        event_type: Optional[str] = None,
        user: Optional[str] = None,
        resource: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Get audit events with filters.

        Args:
            event_type: Filter by event type
            user: Filter by user
            resource: Filter by resource
            level: Filter by severity level
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        events = self.events

        if event_type:
            event_type_enum = AuditEventType[event_type.upper()]
            events = [e for e in events if e.event_type == event_type_enum]

        if user:
            events = [e for e in events if e.user == user]

        if resource:
            events = [e for e in events if e.resource == resource]

        if level:
            level_enum = AuditLevel[level.upper()]
            events = [e for e in events if e.level == level_enum]

        # Return most recent first
        events = sorted(events, key=lambda x: x.timestamp, reverse=True)
        return events[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit statistics.

        Returns:
            Statistics dictionary
        """
        total_events = len(self.events)

        # Count by type
        type_counts = {}
        for event in self.events:
            event_type = event.event_type.value
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Count by level
        level_counts = {}
        for event in self.events:
            level = event.level.value
            level_counts[level] = level_counts.get(level, 0) + 1

        # Count by user
        user_counts = {}
        for event in self.events:
            if event.user:
                user_counts[event.user] = user_counts.get(event.user, 0) + 1

        return {
            "total_events": total_events,
            "events_by_type": type_counts,
            "events_by_level": level_counts,
            "top_users": dict(sorted(
                user_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "log_file": str(self.log_file) if self.log_file else None
        }

    def clear_events(self):
        """Clear all events from memory."""
        self.events.clear()

    def flush(self):
        """Flush all events to file."""
        if not self.log_file:
            return

        try:
            with open(self.log_file, 'w') as f:
                for event in self.events:
                    f.write(event.to_json() + '\n')
        except Exception as e:
            logger.error(f"Failed to flush audit log: {e}")

    def export_events(
        self,
        output_file: str,
        format: str = "json"
    ):
        """
        Export events to file.

        Args:
            output_file: Output file path
            format: Export format (json or csv)
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, 'w') as f:
                events_dict = [e.to_dict() for e in self.events]
                json.dump(events_dict, f, indent=2)

        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                if not self.events:
                    return

                fieldnames = list(self.events[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for event in self.events:
                    row = event.to_dict()
                    # Convert metadata to string
                    row['metadata'] = json.dumps(row['metadata'])
                    writer.writerow(row)


__all__ = [
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditLevel"
]
