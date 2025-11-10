"""
NeuroLake FastAPI Main Application

Production-ready FastAPI application with comprehensive monitoring,
security, and health checks.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import uvicorn

# Import NeuroLake components
from neurolake.config import get_settings
from neurolake.db import DatabaseManager
from neurolake.cache import CacheManager
from neurolake.monitoring.instrumentation import setup_monitoring
from neurolake.api.middleware.security import SecurityHeadersMiddleware
from neurolake.api.middleware.rate_limit import RateLimitMiddleware
from neurolake.api.middleware.csrf import CSRFMiddleware

# Import routers
from neurolake.api.routers import (
    queries_v1,
    data_v1,
    catalog_v1,
    ncf_v1,
    auth_v1,
    pipelines_v1,
    agents_v1,
    audit_v1,
    compliance_v1,
    integrations_v1,
    jobs_v1,
    health,
    metrics as metrics_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Settings
settings = get_settings()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'neurolake_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'neurolake_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)
ACTIVE_CONNECTIONS = Gauge(
    'neurolake_api_active_connections',
    'Active API connections'
)
DB_CONNECTION_POOL_SIZE = Gauge(
    'neurolake_db_pool_size',
    'Database connection pool size'
)
CACHE_HIT_RATE = Gauge(
    'neurolake_cache_hit_rate',
    'Cache hit rate percentage'
)

# Global service instances
db_manager: Optional[DatabaseManager] = None
cache_manager: Optional[CacheManager] = None
tracer = trace.get_tracer(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown of all services.
    """
    global db_manager, cache_manager

    # Startup
    logger.info("=" * 60)
    logger.info("Starting NeuroLake API...")
    logger.info("=" * 60)

    try:
        # Initialize database connections
        logger.info("Initializing database connection pool...")
        db_manager = DatabaseManager()
        logger.info(f"✓ Database pool initialized: {settings.database.pool_size} connections")

        # Initialize cache
        logger.info("Initializing cache manager...")
        cache_manager = CacheManager(
            redis_host=settings.redis.host,
            redis_port=settings.redis.port,
            default_ttl=settings.redis.default_ttl
        )
        logger.info("✓ Cache manager initialized")

        # Initialize storage (MinIO)
        if settings.storage:
            logger.info("Initializing storage manager...")
            # Storage is initialized on-demand
            logger.info("✓ Storage manager configured")

        # Initialize monitoring
        logger.info("Setting up monitoring and instrumentation...")
        setup_monitoring(app)
        logger.info("✓ Monitoring instrumentation active")

        # Update metrics
        DB_CONNECTION_POOL_SIZE.set(settings.database.pool_size)

        logger.info("=" * 60)
        logger.info("✓ NeuroLake API started successfully")
        logger.info(f"  Version: {app.version}")
        logger.info(f"  Environment: {settings.api.environment}")
        logger.info(f"  Docs: http://localhost:{settings.api.port}/docs")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ Failed to start NeuroLake API: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down NeuroLake API...")
    logger.info("=" * 60)

    try:
        # Close database connections
        if db_manager:
            logger.info("Closing database connections...")
            db_manager.close()
            logger.info("✓ Database connections closed")

        # Close cache connections
        if cache_manager:
            logger.info("Closing cache connections...")
            cache_manager.close()
            logger.info("✓ Cache connections closed")

        # Cleanup resources
        logger.info("Cleaning up resources...")
        # Add any additional cleanup here
        logger.info("✓ Resources cleaned up")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("✓ NeuroLake API shut down complete")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="NeuroLake API",
    description="AI-Native Data Platform with NCF Storage Format",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "NeuroLake Team",
        "url": "https://github.com/yourusername/neurolake",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Security middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware, secret_key=settings.api.secret_key)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.api.rate_limit_per_minute)

# Trust only specific hosts in production
if settings.api.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.api.allowed_hosts
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Track request metrics for monitoring."""
    import time

    ACTIVE_CONNECTIONS.inc()
    start_time = time.time()

    try:
        response = await call_next(request)

        # Track metrics
        process_time = time.time() - start_time
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)

        return response
    finally:
        ACTIVE_CONNECTIONS.dec()


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": "NeuroLake API",
        "version": "1.0.0",
        "description": "AI-Native Data Platform",
        "status": "running",
        "environment": settings.api.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "metrics": "/metrics",
            "openapi": "/api/v1/openapi.json"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging and tracing."""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )

    # Track error in metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=500
    ).inc()

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.api.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(metrics_router.router, tags=["Metrics"])
app.include_router(auth_v1.router, tags=["Authentication & Authorization"])  # Auth router (prefix already defined)
app.include_router(queries_v1.router, prefix="/api/v1/queries", tags=["Queries v1"])
app.include_router(data_v1.router, prefix="/api/v1/data", tags=["Data v1"])
app.include_router(catalog_v1.router, prefix="/api/v1/catalog", tags=["Catalog v1"])
app.include_router(ncf_v1.router, prefix="/api/v1/ncf", tags=["NCF v1"])
app.include_router(pipelines_v1.router, prefix="/api/v1/pipelines", tags=["Pipelines v1"])
app.include_router(agents_v1.router, prefix="/api/v1/agents", tags=["Agents v1"])
app.include_router(audit_v1.router, prefix="/api/v1/audit", tags=["Audit v1"])
app.include_router(compliance_v1.router, prefix="/api/v1/compliance", tags=["Compliance v1"])
app.include_router(integrations_v1.router, prefix="/api/v1/integrations", tags=["Integrations v1"])
app.include_router(jobs_v1.router, prefix="/api/v1/jobs", tags=["Jobs v1"])

# Setup OpenTelemetry instrumentation
FastAPIInstrumentor.instrument_app(app)


if __name__ == "__main__":
    # For development only
    uvicorn.run(
        "neurolake.api.main:app",
        host="0.0.0.0",
        port=settings.api.port,
        reload=settings.api.debug,
        log_level="info" if settings.api.debug else "warning",
        access_log=settings.api.debug
    )
