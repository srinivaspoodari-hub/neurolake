"""API routers"""

from . import (
    queries_v1,
    data_v1,
    catalog_v1,
    ncf_v1,
    health,
    metrics,
    auth_v1,
    pipelines_v1,
    agents_v1,
    audit_v1,
    compliance_v1,
    integrations_v1
)

__all__ = [
    "queries_v1",
    "data_v1",
    "catalog_v1",
    "ncf_v1",
    "health",
    "metrics",
    "auth_v1",
    "pipelines_v1",
    "agents_v1",
    "audit_v1",
    "compliance_v1",
    "integrations_v1"
]
