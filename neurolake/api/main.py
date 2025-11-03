"""
NeuroLake FastAPI Main Application

Main FastAPI application entry point for NeuroLake API.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting NeuroLake API...")
    logger.info("Initializing services...")

    # TODO: Initialize database connections
    # TODO: Initialize cache
    # TODO: Initialize storage

    logger.info("NeuroLake API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down NeuroLake API...")

    # TODO: Close database connections
    # TODO: Close cache connections
    # TODO: Cleanup resources

    logger.info("NeuroLake API shut down complete")


# Create FastAPI application
app = FastAPI(
    title="NeuroLake API",
    description="AI-Native Data Platform with NCF Storage Format",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": "NeuroLake API",
        "version": "0.1.0",
        "description": "AI-Native Data Platform",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "running",
            "database": "connected",  # TODO: Add real health check
            "cache": "connected",     # TODO: Add real health check
            "storage": "connected"    # TODO: Add real health check
        }
    }


@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes.

    Returns:
        Readiness status
    """
    # TODO: Add actual readiness checks
    # - Database connection
    # - Required services availability
    # - Configuration loaded

    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def metrics() -> str:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    # TODO: Implement actual metrics collection
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    metrics_text = """
# HELP neurolake_api_requests_total Total API requests
# TYPE neurolake_api_requests_total counter
neurolake_api_requests_total 0

# HELP neurolake_api_request_duration_seconds API request duration
# TYPE neurolake_api_request_duration_seconds histogram
neurolake_api_request_duration_seconds_bucket{le="0.1"} 0
neurolake_api_request_duration_seconds_bucket{le="+Inf"} 0
neurolake_api_request_duration_seconds_sum 0
neurolake_api_request_duration_seconds_count 0
"""

    return metrics_text


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# API Routers (to be added)
# from neurolake.api.routers import queries, data, pipelines, agents
# app.include_router(queries.router, prefix="/api/v1/queries", tags=["queries"])
# app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
# app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
# app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])


if __name__ == "__main__":
    # For development only
    uvicorn.run(
        "neurolake.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
