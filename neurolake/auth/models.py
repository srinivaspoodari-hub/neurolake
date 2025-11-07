"""
RBAC Database Models
SQLAlchemy models for User, Role, Permission management
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
import json

Base = declarative_base()


# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime, default=datetime.utcnow),
    Column('assigned_by', Integer, ForeignKey('users.id'), nullable=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime, default=datetime.utcnow)
)


class User(Base):
    """
    User Model
    Represents a user in the system with authentication and authorization
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    password_changed_at = Column(DateTime, nullable=True)
    require_password_change = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 compatible

    # API Key (optional for service accounts)
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    api_key_created_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Preferences (JSON)
    preferences = Column(Text, nullable=True)  # Store as JSON string

    # Relationships
    roles = relationship('Role', secondary=user_roles, back_populates='users', lazy='joined')
    created_by_user = relationship('User', remote_side=[id], foreign_keys=[created_by])
    audit_logs = relationship('AuditLog', back_populates='user', cascade='all, delete-orphan')

    @hybrid_property
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True

        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        if self.is_superuser:
            return True
        return any(role.name == role_name for role in self.roles)

    def has_any_role(self, role_names: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        if self.is_superuser:
            return True
        return any(role.name in role_names for role in self.roles)

    def get_permissions(self) -> List[str]:
        """Get all permissions for this user"""
        if self.is_superuser:
            return ['*']  # Superuser has all permissions

        permissions = set()
        for role in self.roles:
            permissions.update(perm.name for perm in role.permissions)
        return list(permissions)

    def get_preferences_dict(self) -> dict:
        """Get preferences as dictionary"""
        if self.preferences:
            try:
                return json.loads(self.preferences)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_preferences(self, prefs: dict):
        """Set preferences from dictionary"""
        self.preferences = json.dumps(prefs)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_superuser': self.is_superuser,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'roles': [role.name for role in self.roles],
            'permissions': self.get_permissions()
        }

        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'is_locked': self.is_locked,
                'locked_until': self.locked_until.isoformat() if self.locked_until else None,
                'last_login_ip': self.last_login_ip,
                'require_password_change': self.require_password_change
            })

        return data


class Role(Base):
    """
    Role Model
    Represents a role with associated permissions
    """
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Role hierarchy
    priority = Column(Integer, default=0)  # Higher number = higher priority

    # Status
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System roles can't be deleted

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship('User', secondary=user_roles, back_populates='roles')
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles', lazy='joined')

    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission"""
        return any(perm.name == permission_name for perm in self.permissions)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'priority': self.priority,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'permissions': [perm.name for perm in self.permissions],
            'user_count': len(self.users)
        }


class Permission(Base):
    """
    Permission Model
    Represents a specific permission (e.g., 'query:execute', 'catalog:read')
    """
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)  # e.g., 'query:execute'
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Permission categorization
    resource = Column(String(100), index=True, nullable=False)  # e.g., 'query', 'catalog', 'user'
    action = Column(String(100), index=True, nullable=False)    # e.g., 'read', 'write', 'delete'

    # Status
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'resource': self.resource,
            'action': self.action,
            'is_active': self.is_active
        }


class AuditLog(Base):
    """
    Audit Log Model
    Tracks all security-relevant actions
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)

    # Who
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    username = Column(String(100), nullable=True)  # Store username for historical purposes

    # What
    action = Column(String(100), index=True, nullable=False)  # e.g., 'login', 'query_execute', 'user_create'
    resource_type = Column(String(100), index=True, nullable=True)  # e.g., 'user', 'query', 'dataset'
    resource_id = Column(String(255), nullable=True)

    # How
    status = Column(String(50), index=True, nullable=False)  # 'success', 'failure', 'denied'
    details = Column(Text, nullable=True)  # JSON string with additional details

    # When & Where
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship('User', back_populates='audit_logs')

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'status': self.status,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address
        }


# Additional models for session management (optional, for stateful sessions)
class Session(Base):
    """
    Session Model (Optional)
    For tracking active user sessions if needed
    """
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Session info
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Security
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)

    def is_valid(self) -> bool:
        """Check if session is still valid"""
        if not self.is_active or self.revoked_at:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class UserRole(Base):
    """
    Extended User-Role relationship with additional metadata
    (Alternative to simple association table if you need more info)
    """
    __tablename__ = 'user_role_assignments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)

    # Assignment metadata
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional: time-limited roles

    # Constraints or conditions
    conditions = Column(Text, nullable=True)  # JSON string for conditional access


class RolePermission(Base):
    """
    Extended Role-Permission relationship
    (Alternative if you need more metadata)
    """
    __tablename__ = 'role_permission_assignments'

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)

    # Grant metadata
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Constraints
    conditions = Column(Text, nullable=True)  # JSON for conditional permissions
