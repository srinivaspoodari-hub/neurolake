"""
API Dependencies

Common dependencies for NeuroLake API endpoints including authentication,
database sessions, and permission checking.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from neurolake.db import get_db_session
from neurolake.auth.models import User
from neurolake.auth.jwt_handler import JWTHandler
from neurolake.auth.rbac import RBACManager

# HTTP Bearer security scheme
security = HTTPBearer()


# ============================================================================
# DATABASE DEPENDENCIES
# ============================================================================

def get_db() -> Session:
    """
    Get database session dependency.

    Yields:
        Database session
    """
    return get_db_session()


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP bearer token credentials
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Verify JWT token
    payload = JWTHandler.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (already checked in get_current_user).

    Args:
        current_user: Current user from token

    Returns:
        Active User object
    """
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superuser (admin only).

    Args:
        current_user: Current active user

    Returns:
        User object if superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superuser access required."
        )
    return current_user


# ============================================================================
# OPTIONAL AUTHENTICATION (for public + authenticated endpoints)
# ============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    Useful for endpoints that work with or without auth.

    Args:
        credentials: Optional HTTP bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = JWTHandler.verify_access_token(token)

        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()
        if user and user.is_active:
            return user

        return None
    except Exception:
        return None


# ============================================================================
# PERMISSION CHECKING DEPENDENCIES
# ============================================================================

class PermissionChecker:
    """
    Dependency class for checking user permissions.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: User = Depends(PermissionChecker("admin:access"))
        ):
            return {"message": "Admin access granted"}
    """

    def __init__(self, permission: str):
        """
        Initialize permission checker.

        Args:
            permission: Required permission name (e.g., "query:execute")
        """
        self.permission = permission

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        """
        Check if user has required permission.

        Args:
            current_user: Current authenticated user
            db: Database session

        Returns:
            User object if permission granted

        Raises:
            HTTPException: If permission denied
        """
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user

        # Check permission
        if not current_user.has_permission(self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {self.permission}"
            )

        return current_user


class RoleChecker:
    """
    Dependency class for checking user roles.

    Usage:
        @router.get("/analyst")
        async def analyst_endpoint(
            user: User = Depends(RoleChecker("data_analyst"))
        ):
            return {"message": "Analyst access granted"}
    """

    def __init__(self, role: str):
        """
        Initialize role checker.

        Args:
            role: Required role name
        """
        self.role = role

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Check if user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            User object if role granted

        Raises:
            HTTPException: If role denied
        """
        # Superusers have all roles
        if current_user.is_superuser:
            return current_user

        # Check role
        if not current_user.has_role(self.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {self.role}"
            )

        return current_user


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_db',
    'get_current_user',
    'get_current_active_user',
    'get_current_superuser',
    'get_current_user_optional',
    'PermissionChecker',
    'RoleChecker',
]
