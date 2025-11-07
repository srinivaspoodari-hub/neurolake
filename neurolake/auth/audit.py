"""
Audit Logger
Security and compliance audit logging
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from .models import AuditLog


class AuditLogger:
    """
    Audit Logger
    Logs all security-relevant actions for compliance and security monitoring
    """

    def __init__(self, db: Session):
        """
        Initialize audit logger

        Args:
            db: Database session
        """
        self.db = db

    def log_action(
        self,
        action: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit event

        Args:
            action: Action performed (e.g., 'login', 'query_execute', 'user_create')
            status: Status of action ('success', 'failure', 'denied')
            user_id: ID of user performing action
            username: Username (for historical purposes)
            resource_type: Type of resource affected (e.g., 'user', 'query', 'dataset')
            resource_id: ID of affected resource
            details: Additional details (can be JSON string)
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog object
        """
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent
        )

        try:
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            return audit_log
        except Exception as e:
            print(f"Failed to log audit: {e}")
            self.db.rollback()
            return audit_log

    def log_authentication(
        self,
        username: str,
        success: bool,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log authentication attempt

        Args:
            username: Username attempting to authenticate
            success: Whether authentication succeeded
            user_id: User ID if successful
            ip_address: Client IP
            details: Additional details
        """
        self.log_action(
            action='authentication',
            status='success' if success else 'failure',
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details
        )

    def log_authorization(
        self,
        user_id: int,
        action: str,
        allowed: bool,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log authorization check

        Args:
            user_id: User ID
            action: Action being authorized
            allowed: Whether authorization was granted
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
        """
        self.log_action(
            action=f'authorize_{action}',
            status='success' if allowed else 'denied',
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_data_access(
        self,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log data access

        Args:
            user_id: User ID
            resource_type: Type of data accessed
            resource_id: Data identifier
            action: Action performed ('read', 'write', 'delete')
            ip_address: Client IP
            details: Additional details
        """
        self.log_action(
            action=f'data_{action}',
            status='success',
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details
        )

    def log_configuration_change(
        self,
        user_id: int,
        resource_type: str,
        resource_id: str,
        details: str
    ):
        """
        Log configuration change

        Args:
            user_id: User ID making change
            resource_type: Type of configuration
            resource_id: Configuration identifier
            details: Details of change
        """
        self.log_action(
            action='config_change',
            status='success',
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_permission_change(
        self,
        user_id: int,
        target_user_id: int,
        action: str,
        details: str
    ):
        """
        Log permission or role change

        Args:
            user_id: User ID making change
            target_user_id: User ID being modified
            action: Action performed ('role_add', 'role_remove', 'permission_grant')
            details: Details of change
        """
        self.log_action(
            action=action,
            status='success',
            user_id=user_id,
            resource_type='user',
            resource_id=str(target_user_id),
            details=details
        )

    def get_user_activity(
        self,
        user_id: int,
        limit: int = 100,
        action_filter: Optional[str] = None
    ):
        """
        Get recent activity for a user

        Args:
            user_id: User ID
            limit: Max number of records
            action_filter: Optional action filter

        Returns:
            List of audit log entries
        """
        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if action_filter:
            query = query.filter(AuditLog.action == action_filter)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        return query.all()

    def get_failed_logins(
        self,
        minutes: int = 60,
        limit: int = 100
    ):
        """
        Get recent failed login attempts

        Args:
            minutes: Time window in minutes
            limit: Max number of records

        Returns:
            List of failed login attempts
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        query = self.db.query(AuditLog).filter(
            AuditLog.action == 'authentication',
            AuditLog.status == 'failure',
            AuditLog.timestamp >= cutoff_time
        ).order_by(AuditLog.timestamp.desc()).limit(limit)

        return query.all()

    def get_suspicious_activity(
        self,
        hours: int = 24,
        threshold: int = 5
    ):
        """
        Detect suspicious activity (multiple failed attempts from same IP)

        Args:
            hours: Time window in hours
            threshold: Number of failures to flag as suspicious

        Returns:
            List of suspicious IP addresses and their failure counts
        """
        from sqlalchemy import func
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        suspicious = self.db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('failure_count')
        ).filter(
            AuditLog.status.in_(['failure', 'denied']),
            AuditLog.timestamp >= cutoff_time,
            AuditLog.ip_address.isnot(None)
        ).group_by(
            AuditLog.ip_address
        ).having(
            func.count(AuditLog.id) >= threshold
        ).all()

        return [
            {'ip_address': ip, 'failure_count': count}
            for ip, count in suspicious
        ]

    def get_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None,
        action: Optional[str] = None
    ):
        """
        Generate audit report for a date range

        Args:
            start_date: Start of date range
            end_date: End of date range
            user_id: Optional user ID filter
            action: Optional action filter

        Returns:
            Dictionary with audit statistics and entries
        """
        from sqlalchemy import func

        query = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        )

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        # Get statistics
        total_events = query.count()

        success_count = query.filter(AuditLog.status == 'success').count()
        failure_count = query.filter(AuditLog.status == 'failure').count()
        denied_count = query.filter(AuditLog.status == 'denied').count()

        # Get top actions
        top_actions = self.db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).group_by(
            AuditLog.action
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()

        # Get recent events
        recent_events = query.order_by(AuditLog.timestamp.desc()).limit(100).all()

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'statistics': {
                'total_events': total_events,
                'success_count': success_count,
                'failure_count': failure_count,
                'denied_count': denied_count,
                'success_rate': (success_count / total_events * 100) if total_events > 0 else 0
            },
            'top_actions': [
                {'action': action, 'count': count}
                for action, count in top_actions
            ],
            'recent_events': [event.to_dict() for event in recent_events]
        }
