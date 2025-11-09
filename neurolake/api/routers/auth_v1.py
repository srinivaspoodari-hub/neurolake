"""
Authentication and Authorization Router (v1)

This module provides authentication, user management, and RBAC endpoints.
It wraps the auth.api module to maintain consistent API versioning.
"""

from neurolake.auth.api import router

# Re-export the router from auth.api
# The router is already configured with prefix="/api/auth"
# and all necessary endpoints

__all__ = ['router']
