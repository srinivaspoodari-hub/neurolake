"""
CSRF Protection Middleware

Cross-Site Request Forgery protection for state-changing operations.
"""

import secrets
import hmac
import hashlib
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_403_FORBIDDEN


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.

    Validates CSRF tokens for state-changing requests (POST, PUT, DELETE, PATCH).
    Safe methods (GET, HEAD, OPTIONS) are exempted.

    Args:
        secret_key: Secret key for HMAC token generation
        header_name: HTTP header name for CSRF token
        cookie_name: Cookie name for CSRF token
        exempt_paths: Paths to exempt from CSRF protection
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    def __init__(
        self,
        app,
        secret_key: str,
        header_name: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        exempt_paths: list = None
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.exempt_paths = set(exempt_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ])

    def _generate_token(self) -> str:
        """Generate a new CSRF token."""
        random_value = secrets.token_hex(32)
        signature = hmac.new(
            self.secret_key,
            random_value.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{random_value}.{signature}"

    def _validate_token(self, token: str) -> bool:
        """
        Validate a CSRF token.

        Returns:
            True if token is valid, False otherwise
        """
        if not token or "." not in token:
            return False

        try:
            random_value, signature = token.rsplit(".", 1)

            expected_signature = hmac.new(
                self.secret_key,
                random_value.encode(),
                hashlib.sha256
            ).hexdigest()

            # Use constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    def _should_exempt(self, request: Request) -> bool:
        """Check if request should be exempted from CSRF protection."""
        # Exempt safe methods
        if request.method in self.SAFE_METHODS:
            return True

        # Exempt specific paths
        if request.url.path in self.exempt_paths:
            return True

        # Exempt API documentation
        if request.url.path.startswith(("/docs", "/redoc", "/openapi")):
            return True

        return False

    async def dispatch(self, request: Request, call_next):
        # Check if request should be exempted
        if self._should_exempt(request):
            response = await call_next(request)

            # Add new CSRF token to response if none exists
            if self.cookie_name not in request.cookies:
                token = self._generate_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=token,
                    httponly=True,
                    samesite="lax",
                    secure=request.url.scheme == "https"
                )

            return response

        # Validate CSRF token for state-changing requests
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)

        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF token missing",
                    "message": "CSRF token required for this request",
                    "required_header": self.header_name,
                    "required_cookie": self.cookie_name
                }
            )

        if cookie_token != header_token:
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF token mismatch",
                    "message": "CSRF token in header does not match cookie"
                }
            )

        if not self._validate_token(cookie_token):
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "Invalid CSRF token",
                    "message": "CSRF token signature is invalid"
                }
            )

        # Token is valid, process request
        response = await call_next(request)

        # Rotate token after use (optional, for enhanced security)
        # Uncomment to enable token rotation
        # new_token = self._generate_token()
        # response.set_cookie(
        #     key=self.cookie_name,
        #     value=new_token,
        #     httponly=True,
        #     samesite="lax",
        #     secure=request.url.scheme == "https"
        # )

        return response
