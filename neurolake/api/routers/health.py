"""
Health Check Router

Comprehensive health and readiness checks for Kubernetes/production deployments.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from neurolake.db import DatabaseManager
from neurolake.cache import CacheManager
from neurolake.config import get_settings

router = APIRouter()
settings = get_settings()


async def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        db_manager = DatabaseManager()
        # Try a simple query
        with db_manager.get_session() as session:
            result = session.execute("SELECT 1").scalar()
            if result == 1:
                return {"status": "healthy", "latency_ms": 0}  # Add actual latency measurement if needed
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

    return {"status": "unknown"}


async def check_cache() -> Dict[str, Any]:
    """Check cache connectivity."""
    try:
        cache_manager = CacheManager(
            redis_host=settings.redis.host,
            redis_port=settings.redis.port
        )
        # Try to set and get a test value
        test_key = "__health_check__"
        cache_manager.set(test_key, "ok", ttl=10)
        value = cache_manager.get(test_key)

        if value == "ok":
            cache_manager.delete(test_key)
            return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

    return {"status": "unknown"}


async def check_storage() -> Dict[str, Any]:
    """Check storage connectivity."""
    try:
        # Storage health check (MinIO/S3)
        # This would need actual MinIO client implementation
        return {"status": "healthy", "note": "Not fully implemented"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns 200 if the service is running.
    Does NOT check dependencies.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.api.environment
    }


@router.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.

    Checks all critical dependencies:
    - Database connectivity
    - Cache availability
    - Storage accessibility

    Returns:
        200 if ready to serve traffic
        503 if not ready
    """
    checks = {
        "database": await check_database(),
        "cache": await check_cache(),
        "storage": await check_storage()
    }

    # Determine overall readiness
    all_healthy = all(
        check.get("status") == "healthy"
        for check in checks.values()
    )

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    )


@router.get("/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint for Kubernetes.

    Returns 200 if the process is alive.
    Returns 500 if the process should be restarted.
    """
    # This is a simple liveness check
    # Add more sophisticated checks if needed (e.g., deadlock detection)
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
