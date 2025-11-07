"""
Authentication and User Management API
REST API endpoints for authentication, user management, and RBAC
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .models import User, Role, Permission
from .auth_service import AuthService
from .rbac import RBACManager, get_current_user, get_current_active_user, get_current_superuser
from .audit import AuditLogger


# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    roles: Optional[List[str]] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    user_id: int
    new_password: str = Field(..., min_length=8)
    require_change: bool = True


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    priority: int = 0


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    priority: int
    is_active: bool
    is_system: bool
    permissions: List[str]
    user_count: int

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    name: str = Field(..., pattern=r'^[a-z_]+:[a-z_]+$')
    display_name: Optional[str] = None
    description: Optional[str] = None
    resource: str
    action: str


class PermissionResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    resource: str
    action: str
    is_active: bool

    class Config:
        from_attributes = True


class RoleAssignmentRequest(BaseModel):
    role_name: str


class PermissionAssignmentRequest(BaseModel):
    permission_name: str


# Router
router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])

# Dependency to get database session
# NOTE: You'll need to implement this based on your database setup
def get_db():
    """Get database session - implement based on your setup"""
    # Example implementation:
    # from your_db_module import SessionLocal
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    raise NotImplementedError("Database session dependency not implemented")


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user

    - **username**: Unique username (3-100 characters)
    - **email**: Valid email address
    - **password**: Strong password (min 8 characters)
    - **full_name**: Optional full name
    - **roles**: Optional list of role names
    """
    auth_service = AuthService(db)

    user, error = auth_service.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role_names=user_data.roles if user_data.roles else None
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens

    - **username**: Username or email
    - **password**: Password
    """
    auth_service = AuthService(db)

    # Get client IP
    client_ip = request.client.host if request.client else None

    # Authenticate
    user, error = auth_service.authenticate(
        username=credentials.username,
        password=credentials.password,
        ip_address=client_ip
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    tokens = auth_service.create_login_tokens(user)

    return LoginResponse(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        token_type=tokens['token_type'],
        expires_in=tokens['expires_in'],
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/token", response_model=LoginResponse)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login endpoint

    - **username**: Username or email
    - **password**: Password
    """
    auth_service = AuthService(db)

    client_ip = request.client.host if request and request.client else None

    user, error = auth_service.authenticate(
        username=form_data.username,
        password=form_data.password,
        ip_address=client_ip
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = auth_service.create_login_tokens(user)

    return LoginResponse(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        token_type=tokens['token_type'],
        expires_in=tokens['expires_in'],
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Get new access token using refresh token

    - **refresh_token**: Valid refresh token
    """
    auth_service = AuthService(db)

    new_access_token = auth_service.refresh_token(refresh_token)

    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password

    - **old_password**: Current password
    - **new_password**: New password (min 8 characters)
    """
    auth_service = AuthService(db)

    success, error = auth_service.change_password(
        user_id=current_user.id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Password changed successfully"}


# ============================================================================
# USER MANAGEMENT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    List all users (Admin only)

    - **skip**: Number of records to skip
    - **limit**: Max number of records to return
    """
    users = db.query(User).offset(skip).limit(limit).all()

    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Update user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_data.email:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete user (Admin only)
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: PasswordResetRequest,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Reset user password (Admin only)
    """
    auth_service = AuthService(db)

    success, error = auth_service.reset_password(
        user_id=user_id,
        new_password=password_data.new_password,
        require_change=password_data.require_change
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Password reset successfully"}


@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Unlock user account (Admin only)
    """
    auth_service = AuthService(db)

    success, error = auth_service.unlock_account(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Account unlocked successfully"}


@router.post("/users/{user_id}/api-key")
async def generate_user_api_key(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Generate API key for user (Admin only)
    """
    auth_service = AuthService(db)

    api_key, error = auth_service.generate_api_key(user_id)

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"api_key": api_key}


@router.delete("/users/{user_id}/api-key")
async def revoke_user_api_key(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Revoke user's API key (Admin only)
    """
    auth_service = AuthService(db)

    success, error = auth_service.revoke_api_key(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "API key revoked successfully"}


# ============================================================================
# ROLE MANAGEMENT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all roles
    """
    roles = db.query(Role).all()

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            priority=role.priority,
            is_active=role.is_active,
            is_system=role.is_system,
            permissions=[perm.name for perm in role.permissions],
            user_count=len(role.users)
        )
        for role in roles
    ]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Create new role (Admin only)
    """
    # Check if role already exists
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists")

    role = Role(
        name=role_data.name,
        display_name=role_data.display_name or role_data.name,
        description=role_data.description,
        priority=role_data.priority,
        is_active=True,
        is_system=False
    )

    db.add(role)
    db.commit()
    db.refresh(role)

    return RoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        priority=role.priority,
        is_active=role.is_active,
        is_system=role.is_system,
        permissions=[],
        user_count=0
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get role by ID
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return RoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        priority=role.priority,
        is_active=role.is_active,
        is_system=role.is_system,
        permissions=[perm.name for perm in role.permissions],
        user_count=len(role.users)
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Update role (Admin only)
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system role"
        )

    if role_data.display_name is not None:
        role.display_name = role_data.display_name
    if role_data.description is not None:
        role.description = role_data.description
    if role_data.priority is not None:
        role.priority = role_data.priority
    if role_data.is_active is not None:
        role.is_active = role_data.is_active

    db.commit()
    db.refresh(role)

    return RoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        priority=role.priority,
        is_active=role.is_active,
        is_system=role.is_system,
        permissions=[perm.name for perm in role.permissions],
        user_count=len(role.users)
    )


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete role (Admin only)
    Cannot delete system roles or roles with assigned users
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system role"
        )

    if len(role.users) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role with {len(role.users)} assigned users"
        )

    db.delete(role)
    db.commit()

    return {"message": "Role deleted successfully"}


# ============================================================================
# PERMISSION MANAGEMENT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all permissions
    """
    permissions = db.query(Permission).all()

    return [
        PermissionResponse(
            id=perm.id,
            name=perm.name,
            display_name=perm.display_name,
            description=perm.description,
            resource=perm.resource,
            action=perm.action,
            is_active=perm.is_active
        )
        for perm in permissions
    ]


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Create new permission (Admin only)
    Permission name must be in format: resource:action (e.g., 'query:execute')
    """
    # Check if permission already exists
    existing = db.query(Permission).filter(Permission.name == permission_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already exists"
        )

    permission = Permission(
        name=permission_data.name,
        display_name=permission_data.display_name or permission_data.name,
        description=permission_data.description,
        resource=permission_data.resource,
        action=permission_data.action,
        is_active=True
    )

    db.add(permission)
    db.commit()
    db.refresh(permission)

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        display_name=permission.display_name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
        is_active=permission.is_active
    )


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get permission by ID
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        display_name=permission.display_name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
        is_active=permission.is_active
    )


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Delete permission (Admin only)
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    db.delete(permission)
    db.commit()

    return {"message": "Permission deleted successfully"}


# ============================================================================
# ROLE-PERMISSION ASSIGNMENT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/roles/{role_id}/permissions", response_model=List[PermissionResponse])
async def list_role_permissions(
    role_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all permissions for a role
    """
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return [
        PermissionResponse(
            id=perm.id,
            name=perm.name,
            display_name=perm.display_name,
            description=perm.description,
            resource=perm.resource,
            action=perm.action,
            is_active=perm.is_active
        )
        for perm in role.permissions
    ]


@router.post("/roles/{role_id}/permissions")
async def grant_permission_to_role(
    role_id: int,
    permission_data: PermissionAssignmentRequest,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Grant permission to role (Admin only)
    """
    rbac_manager = RBACManager(db)

    success = rbac_manager.grant_permission_to_role(
        role_name=None,  # We'll modify this
        permission_name=permission_data.permission_name
    )

    # Get role and permission by ID/name
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    permission = db.query(Permission).filter(
        Permission.name == permission_data.permission_name
    ).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    # Add permission to role if not already present
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()

        # Log action
        audit_logger = AuditLogger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action='permission_grant',
            status='success',
            resource_type='role',
            resource_id=str(role_id),
            details=f"Granted permission '{permission_data.permission_name}' to role '{role.name}'"
        )

    return {"message": f"Permission '{permission_data.permission_name}' granted to role '{role.name}'"}


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def revoke_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Revoke permission from role (Admin only)
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify permissions of system role"
        )

    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()

        # Log action
        audit_logger = AuditLogger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action='permission_revoke',
            status='success',
            resource_type='role',
            resource_id=str(role_id),
            details=f"Revoked permission '{permission.name}' from role '{role.name}'"
        )

    return {"message": f"Permission '{permission.name}' revoked from role '{role.name}'"}


# ============================================================================
# USER-ROLE ASSIGNMENT ENDPOINTS (Admin only)
# ============================================================================

@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def list_user_roles(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all roles for a user
    """
    # Allow users to view their own roles
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            priority=role.priority,
            is_active=role.is_active,
            is_system=role.is_system,
            permissions=[perm.name for perm in role.permissions],
            user_count=len(role.users)
        )
        for role in user.roles
    ]


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: int,
    role_data: RoleAssignmentRequest,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Assign role to user (Admin only)
    """
    rbac_manager = RBACManager(db)

    success = rbac_manager.assign_role(user_id, role_data.role_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role"
        )

    return {"message": f"Role '{role_data.role_name}' assigned to user"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Remove role from user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    rbac_manager = RBACManager(db)
    success = rbac_manager.remove_role(user_id, role.name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove role"
        )

    return {"message": f"Role '{role.name}' removed from user"}


# ============================================================================
# AUDIT LOG ENDPOINTS (Admin only)
# ============================================================================

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    status: str
    details: Optional[str]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]

    class Config:
        from_attributes = True


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def query_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Query audit logs with filters (Admin only)

    - **skip**: Number of records to skip
    - **limit**: Max number of records to return
    - **user_id**: Filter by user ID
    - **action**: Filter by action
    - **status**: Filter by status (success, failure, denied)
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    """
    from .models import AuditLog

    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if status:
        query = query.filter(AuditLog.status == status)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    query = query.order_by(AuditLog.timestamp.desc())
    logs = query.offset(skip).limit(limit).all()

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            status=log.status,
            details=log.details,
            timestamp=log.timestamp,
            ip_address=log.ip_address,
            user_agent=log.user_agent
        )
        for log in logs
    ]


@router.get("/audit-logs/suspicious")
async def get_suspicious_activity(
    hours: int = 24,
    threshold: int = 5,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Get suspicious activity (multiple failed attempts from same IP)

    - **hours**: Time window in hours (default: 24)
    - **threshold**: Minimum number of failures to flag (default: 5)
    """
    audit_logger = AuditLogger(db)
    suspicious = audit_logger.get_suspicious_activity(hours=hours, threshold=threshold)

    return {
        "time_window_hours": hours,
        "failure_threshold": threshold,
        "suspicious_ips": suspicious
    }


@router.get("/audit-logs/report")
async def generate_audit_report(
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive audit report for date range

    - **start_date**: Report start date
    - **end_date**: Report end date
    - **user_id**: Optional filter by user
    - **action**: Optional filter by action
    """
    audit_logger = AuditLogger(db)
    report = audit_logger.get_audit_report(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        action=action
    )

    return report


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "service": "NeuroLake Authentication & RBAC",
        "timestamp": datetime.utcnow().isoformat()
    }