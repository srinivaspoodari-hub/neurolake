"""
JWT Handler
JSON Web Token generation and validation
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import JWTError, ExpiredSignatureError, InvalidTokenError


class JWTHandler:
    """
    JWT token generation and validation
    """

    # Configuration (should be loaded from environment in production)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-use-openssl-rand-hex-32")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    @classmethod
    def create_access_token(
        cls,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            data: Dictionary of claims to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        # Encode token
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def create_refresh_token(
        cls,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token

        Args:
            data: Dictionary of claims to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        # Encode token
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token

        Args:
            token: JWT token string to verify

        Returns:
            Dictionary of decoded claims if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            return payload
        except ExpiredSignatureError:
            return None
        except InvalidTokenError:
            return None
        except JWTError:
            return None

    @classmethod
    def verify_access_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify an access token

        Args:
            token: JWT token string to verify

        Returns:
            Dictionary of decoded claims if valid, None otherwise
        """
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    @classmethod
    def verify_refresh_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a refresh token

        Args:
            token: JWT token string to verify

        Returns:
            Dictionary of decoded claims if valid, None otherwise
        """
        payload = cls.verify_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None

    @classmethod
    def get_token_expiry(cls, token: str) -> Optional[datetime]:
        """
        Get expiration datetime from token

        Args:
            token: JWT token string

        Returns:
            Expiration datetime if valid, None otherwise
        """
        try:
            # Decode without verification to get expiry
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
        except Exception:
            pass
        return None

    @classmethod
    def is_token_expired(cls, token: str) -> bool:
        """
        Check if token is expired

        Args:
            token: JWT token string

        Returns:
            True if expired, False otherwise
        """
        expiry = cls.get_token_expiry(token)
        if expiry:
            return datetime.utcnow() > expiry
        return True

    @classmethod
    def create_token_pair(cls, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create both access and refresh tokens

        Args:
            user_data: User data to encode in tokens

        Returns:
            Dictionary with 'access_token' and 'refresh_token'
        """
        access_token = cls.create_access_token(user_data)
        refresh_token = cls.create_refresh_token(user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": cls.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }

    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        payload = cls.verify_refresh_token(refresh_token)
        if not payload:
            return None

        # Create new access token with same user data
        user_data = {k: v for k, v in payload.items() if k not in ['exp', 'iat', 'type']}
        return cls.create_access_token(user_data)

    @classmethod
    def decode_token_without_verification(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without verifying signature (for debugging/inspection)

        Args:
            token: JWT token string

        Returns:
            Dictionary of decoded claims if decodable, None otherwise
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False}
            )
        except Exception:
            return None
