"""
RBAC Manager
Role-Based Access Control implementation with decorators
"""

from functools import wraps
from typing import List, Optional, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .models import User, Role, Permission
from .jwt_handler import JWTHandler
from .audit import AuditLogger


security = HTTPBearer()


class RBACManager:
    """
    RBAC Manager
    Handles permission checking and role management
    """

    def __init__(self, db: Session):
        """
        Initialize RBAC manager

        Args:
            db: Database session
        """
        self.db = db
        self.audit_logger = AuditLogger(db)

    def check_permission(self, user: User, permission_name: str) -> bool:
        """
        Check if user has a specific permission

        Args:
            user: User object
            permission_name: Permission name (e.g., 'query:execute')

        Returns:
            True if user has permission, False otherwise
        """
        if user.is_superuser:
            return True

        return user.has_permission(permission_name)

    def check_role(self, user: User, role_name: str) -> bool:
        """
        Check if user has a specific role

        Args:
            user: User object
            role_name: Role name

        Returns:
            True if user has role, False otherwise
        """
        if user.is_superuser:
            return True

        return user.has_role(role_name)

    def check_any_role(self, user: User, role_names: List[str]) -> bool:
        """
        Check if user has any of the specified roles

        Args:
            user: User object
            role_names: List of role names

        Returns:
            True if user has any role, False otherwise
        """
        if user.is_superuser:
            return True

        return user.has_any_role(role_names)

    def assign_role(self, user_id: int, role_name: str) -> bool:
        """
        Assign role to user

        Args:
            user_id: User ID
            role_name: Role name

        Returns:
            True if successful, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False

        if role not in user.roles:
            user.roles.append(role)
            self.db.commit()

            self.audit_logger.log_action(
                user_id=user_id,
                action='role_assign',
                status='success',
                details=f"Assigned role: {role_name}"
            )

        return True

    def remove_role(self, user_id: int, role_name: str) -> bool:
        """
        Remove role from user

        Args:
            user_id: User ID
            role_name: Role name

        Returns:
            True if successful, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False

        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()

            self.audit_logger.log_action(
                user_id=user_id,
                action='role_remove',
                status='success',
                details=f"Removed role: {role_name}"
            )

        return True

    def grant_permission_to_role(self, role_name: str, permission_name: str) -> bool:
        """
        Grant permission to role

        Args:
            role_name: Role name
            permission_name: Permission name

        Returns:
            True if successful, False otherwise
        """
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False

        permission = self.db.query(Permission).filter(Permission.name == permission_name).first()
        if not permission:
            return False

        if permission not in role.permissions:
            role.permissions.append(permission)
            self.db.commit()

        return True

    def revoke_permission_from_role(self, role_name: str, permission_name: str) -> bool:
        """
        Revoke permission from role

        Args:
            role_name: Role name
            permission_name: Permission name

        Returns:
            True if successful, False otherwise
        """
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False

        permission = self.db.query(Permission).filter(Permission.name == permission_name).first()
        if not permission:
            return False

        if permission in role.permissions:
            role.permissions.remove(permission)
            self.db.commit()

        return True


# Dependency for getting current user from JWT token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends()  # You'll need to provide db dependency
) -> User:
    """
    Get current user from JWT token

    Args:
        credentials: HTTP bearer token
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token
    payload = JWTHandler.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


# Dependency for getting current active user
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user

    Args:
        current_user: Current user from token

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Dependency for getting superuser
async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superuser

    Args:
        current_user: Current active user

    Returns:
        User object if superuser

    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Decorator for permission checking
def require_permission(permission_name: str):
    """
    Decorator to require specific permission

    Args:
        permission_name: Required permission name

    Returns:
        Decorator function

    Example:
        @require_permission('query:execute')
        async def execute_query(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check permission
            if not current_user.has_permission(permission_name):
                # Log denied access
                db = kwargs.get('db')
                if db:
                    audit_logger = AuditLogger(db)
                    audit_logger.log_action(
                        user_id=current_user.id,
                        action=func.__name__,
                        status='denied',
                        details=f"Permission denied: {permission_name}"
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission_name} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Decorator for role checking
def require_role(role_name: str):
    """
    Decorator to require specific role

    Args:
        role_name: Required role name

    Returns:
        Decorator function

    Example:
        @require_role('admin')
        async def admin_function(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check role
            if not current_user.has_role(role_name):
                # Log denied access
                db = kwargs.get('db')
                if db:
                    audit_logger = AuditLogger(db)
                    audit_logger.log_action(
                        user_id=current_user.id,
                        action=func.__name__,
                        status='denied',
                        details=f"Role denied: {role_name}"
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role_name}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Decorator for checking any of multiple roles
def require_any_role(*role_names: str):
    """
    Decorator to require any of multiple roles

    Args:
        role_names: Required role names

    Returns:
        Decorator function

    Example:
        @require_any_role('admin', 'data_engineer')
        async def privileged_function(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check roles
            if not current_user.has_any_role(list(role_names)):
                # Log denied access
                db = kwargs.get('db')
                if db:
                    audit_logger = AuditLogger(db)
                    audit_logger.log_action(
                        user_id=current_user.id,
                        action=func.__name__,
                        status='denied',
                        details=f"Roles denied: {', '.join(role_names)}"
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these roles required: {', '.join(role_names)}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
