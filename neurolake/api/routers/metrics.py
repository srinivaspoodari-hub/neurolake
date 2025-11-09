"""
Metrics Router

Prometheus metrics endpoint.
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/metrics", tags=["Metrics"])
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns all registered Prometheus metrics in text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
