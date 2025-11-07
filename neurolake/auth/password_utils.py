"""
Password Utilities
Secure password hashing and validation using bcrypt
"""

import secrets
import string
from typing import Tuple
from passlib.context import CryptContext


class PasswordUtils:
    """
    Password hashing and validation utilities
    Uses bcrypt for secure password hashing
    """

    # Password context with bcrypt
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Password policy
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return cls.pwd_context.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return cls.pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    @classmethod
    def validate_password_policy(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password against security policy

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"

        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters long"

        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be no more than {cls.MAX_LENGTH} characters long"

        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if cls.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARACTERS for c in password):
            return False, f"Password must contain at least one special character ({cls.SPECIAL_CHARACTERS})"

        # Check for common weak passwords
        weak_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password.lower() in weak_passwords:
            return False, "Password is too common and weak"

        return True, ""

    @classmethod
    def generate_random_password(cls, length: int = 16) -> str:
        """
        Generate a secure random password

        Args:
            length: Length of password (default 16)

        Returns:
            Random password string
        """
        if length < cls.MIN_LENGTH:
            length = cls.MIN_LENGTH

        # Ensure password contains all required character types
        password = []

        if cls.REQUIRE_UPPERCASE:
            password.append(secrets.choice(string.ascii_uppercase))

        if cls.REQUIRE_LOWERCASE:
            password.append(secrets.choice(string.ascii_lowercase))

        if cls.REQUIRE_DIGIT:
            password.append(secrets.choice(string.digits))

        if cls.REQUIRE_SPECIAL:
            password.append(secrets.choice(cls.SPECIAL_CHARACTERS))

        # Fill remaining length with random characters
        all_chars = string.ascii_letters + string.digits + cls.SPECIAL_CHARACTERS
        remaining_length = length - len(password)
        password.extend(secrets.choice(all_chars) for _ in range(remaining_length))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    @classmethod
    def generate_api_key(cls, length: int = 32) -> str:
        """
        Generate a secure API key

        Args:
            length: Length of API key (default 32)

        Returns:
            Random API key string
        """
        return secrets.token_urlsafe(length)

    @classmethod
    def needs_rehash(cls, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated

        Args:
            hashed_password: Hashed password to check

        Returns:
            True if hash needs to be updated
        """
        return cls.pwd_context.needs_update(hashed_password)

    @classmethod
    def get_password_strength(cls, password: str) -> dict:
        """
        Analyze password strength

        Args:
            password: Password to analyze

        Returns:
            Dictionary with strength metrics
        """
        strength = {
            'length': len(password),
            'has_uppercase': any(c.isupper() for c in password),
            'has_lowercase': any(c.islower() for c in password),
            'has_digit': any(c.isdigit() for c in password),
            'has_special': any(c in cls.SPECIAL_CHARACTERS for c in password),
            'score': 0
        }

        # Calculate score (0-100)
        score = 0

        # Length score (up to 30 points)
        if strength['length'] >= cls.MIN_LENGTH:
            score += min(30, (strength['length'] - cls.MIN_LENGTH) * 3 + 10)

        # Character type scores (10 points each)
        if strength['has_uppercase']:
            score += 15
        if strength['has_lowercase']:
            score += 15
        if strength['has_digit']:
            score += 15
        if strength['has_special']:
            score += 15

        # Diversity bonus (up to 10 points)
        unique_chars = len(set(password))
        diversity_ratio = unique_chars / len(password) if len(password) > 0 else 0
        score += int(diversity_ratio * 10)

        strength['score'] = min(100, score)

        # Classify strength
        if strength['score'] < 30:
            strength['classification'] = 'weak'
        elif strength['score'] < 60:
            strength['classification'] = 'moderate'
        elif strength['score'] < 80:
            strength['classification'] = 'strong'
        else:
            strength['classification'] = 'very strong'

        return strength
