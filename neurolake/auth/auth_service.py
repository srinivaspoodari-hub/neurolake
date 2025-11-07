"""
Authentication Service
Core authentication logic including login, registration, password reset
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import User, Role, AuditLog
from .password_utils import PasswordUtils
from .jwt_handler import JWTHandler


class AuthService:
    """
    Authentication Service
    Handles user authentication, registration, and password management
    """

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    def __init__(self, db: Session):
        """
        Initialize auth service

        Args:
            db: Database session
        """
        self.db = db

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role_names: Optional[list] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user

        Args:
            username: Unique username
            email: Unique email
            password: Plain text password
            full_name: User's full name
            role_names: List of role names to assign

        Returns:
            Tuple of (User object if successful, error message if failed)
        """
        # Validate password policy
        is_valid, error_msg = PasswordUtils.validate_password_policy(password)
        if not is_valid:
            return None, error_msg

        # Check if username already exists
        existing_user = self.db.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()

        if existing_user:
            if existing_user.username == username:
                return None, "Username already exists"
            else:
                return None, "Email already exists"

        # Hash password
        hashed_password = PasswordUtils.hash_password(password)

        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False
        )

        # Assign roles
        if role_names:
            roles = self.db.query(Role).filter(Role.name.in_(role_names)).all()
            user.roles = roles
        else:
            # Assign default 'viewer' role
            default_role = self.db.query(Role).filter(Role.name == 'viewer').first()
            if default_role:
                user.roles = [default_role]

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            # Log registration
            self._log_audit(
                user_id=user.id,
                action='user_register',
                status='success',
                details=f"User {username} registered"
            )

            return user, None
        except Exception as e:
            self.db.rollback()
            return None, f"Registration failed: {str(e)}"

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with username and password

        Args:
            username: Username or email
            password: Plain text password
            ip_address: Client IP address

        Returns:
            Tuple of (User object if successful, error message if failed)
        """
        # Find user by username or email
        user = self.db.query(User).filter(
            or_(User.username == username, User.email == username)
        ).first()

        if not user:
            self._log_audit(
                user_id=None,
                username=username,
                action='login_attempt',
                status='failure',
                details="User not found",
                ip_address=ip_address
            )
            return None, "Invalid username or password"

        # Check if account is locked
        if user.is_locked:
            self._log_audit(
                user_id=user.id,
                action='login_attempt',
                status='failure',
                details="Account locked",
                ip_address=ip_address
            )
            return None, f"Account is locked until {user.locked_until.strftime('%Y-%m-%d %H:%M:%S')}"

        # Check if account is active
        if not user.is_active:
            self._log_audit(
                user_id=user.id,
                action='login_attempt',
                status='failure',
                details="Account inactive",
                ip_address=ip_address
            )
            return None, "Account is inactive"

        # Verify password
        if not PasswordUtils.verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1

            # Lock account if too many failed attempts
            if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                self.db.commit()

                self._log_audit(
                    user_id=user.id,
                    action='account_locked',
                    status='failure',
                    details=f"Account locked due to {self.MAX_LOGIN_ATTEMPTS} failed login attempts",
                    ip_address=ip_address
                )
                return None, f"Account locked due to too many failed attempts. Try again after {self.LOCKOUT_DURATION_MINUTES} minutes"

            self.db.commit()

            self._log_audit(
                user_id=user.id,
                action='login_attempt',
                status='failure',
                details=f"Invalid password (attempt {user.failed_login_attempts}/{self.MAX_LOGIN_ATTEMPTS})",
                ip_address=ip_address
            )
            return None, "Invalid username or password"

        # Successful login - reset failed attempts
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        user.last_login_ip = ip_address

        # Check if password needs rehash
        if PasswordUtils.needs_rehash(user.hashed_password):
            user.hashed_password = PasswordUtils.hash_password(password)

        self.db.commit()

        self._log_audit(
            user_id=user.id,
            action='login',
            status='success',
            details="Successful login",
            ip_address=ip_address
        )

        return user, None

    def create_login_tokens(self, user: User) -> Dict[str, str]:
        """
        Create JWT tokens for authenticated user

        Args:
            user: Authenticated user

        Returns:
            Dictionary with access_token and refresh_token
        """
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": [role.name for role in user.roles],
            "is_superuser": user.is_superuser
        }

        return JWTHandler.create_token_pair(token_data)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        return JWTHandler.verify_access_token(token)

    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Create new access token from refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if successful, None otherwise
        """
        return JWTHandler.refresh_access_token(refresh_token)

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        # Verify old password
        if not PasswordUtils.verify_password(old_password, user.hashed_password):
            self._log_audit(
                user_id=user_id,
                action='password_change',
                status='failure',
                details="Invalid old password"
            )
            return False, "Invalid old password"

        # Validate new password
        is_valid, error_msg = PasswordUtils.validate_password_policy(new_password)
        if not is_valid:
            return False, error_msg

        # Check if new password is same as old
        if PasswordUtils.verify_password(new_password, user.hashed_password):
            return False, "New password must be different from old password"

        # Update password
        user.hashed_password = PasswordUtils.hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.require_password_change = False

        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='password_change',
            status='success',
            details="Password changed successfully"
        )

        return True, None

    def reset_password(
        self,
        user_id: int,
        new_password: str,
        require_change: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset user password (admin function)

        Args:
            user_id: User ID
            new_password: New password
            require_change: Require user to change password on next login

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        # Validate new password
        is_valid, error_msg = PasswordUtils.validate_password_policy(new_password)
        if not is_valid:
            return False, error_msg

        # Update password
        user.hashed_password = PasswordUtils.hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.require_password_change = require_change
        user.failed_login_attempts = 0
        user.locked_until = None

        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='password_reset',
            status='success',
            details="Password reset by admin"
        )

        return True, None

    def unlock_account(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Unlock user account

        Args:
            user_id: User ID

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        user.failed_login_attempts = 0
        user.locked_until = None

        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='account_unlock',
            status='success',
            details="Account unlocked"
        )

        return True, None

    def deactivate_user(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Deactivate user account

        Args:
            user_id: User ID

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        user.is_active = False
        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='user_deactivate',
            status='success',
            details="User deactivated"
        )

        return True, None

    def activate_user(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Activate user account

        Args:
            user_id: User ID

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        user.is_active = True
        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='user_activate',
            status='success',
            details="User activated"
        )

        return True, None

    def generate_api_key(self, user_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate API key for user

        Args:
            user_id: User ID

        Returns:
            Tuple of (API key if successful, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None, "User not found"

        api_key = PasswordUtils.generate_api_key()
        user.api_key = api_key
        user.api_key_created_at = datetime.utcnow()

        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='api_key_generate',
            status='success',
            details="API key generated"
        )

        return api_key, None

    def revoke_api_key(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Revoke user's API key

        Args:
            user_id: User ID

        Returns:
            Tuple of (success boolean, error message if failed)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        user.api_key = None
        user.api_key_created_at = None

        self.db.commit()

        self._log_audit(
            user_id=user_id,
            action='api_key_revoke',
            status='success',
            details="API key revoked"
        )

        return True, None

    def verify_api_key(self, api_key: str) -> Optional[User]:
        """
        Verify API key and return user

        Args:
            api_key: API key to verify

        Returns:
            User object if valid, None otherwise
        """
        user = self.db.query(User).filter(
            User.api_key == api_key,
            User.is_active == True
        ).first()

        if user:
            self._log_audit(
                user_id=user.id,
                action='api_key_auth',
                status='success',
                details="API key authentication successful"
            )

        return user

    def _log_audit(
        self,
        action: str,
        status: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        """
        Log audit event

        Args:
            action: Action performed
            status: Status of action (success, failure, denied)
            user_id: User ID performing action
            username: Username (for cases where user doesn't exist)
            details: Additional details
            ip_address: IP address
            resource_type: Type of resource affected
            resource_id: ID of resource affected
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                status=status,
                details=details,
                ip_address=ip_address,
                resource_type=resource_type,
                resource_id=resource_id
            )
            self.db.add(audit_log)
            self.db.commit()
        except Exception as e:
            print(f"Failed to log audit: {e}")
            self.db.rollback()
