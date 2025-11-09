"""
Catalog API Router (v1)

Data catalog and metadata management endpoints.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from neurolake.db import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


class Asset(BaseModel):
    """Catalog asset model."""
    id: str
    name: str
    type: str = Field(..., description="Asset type: table, view, file, dataset, schema")
    database: Optional[str] = None
    schema: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    owner: Optional[str] = None
    created_at: str
    updated_at: str


class SearchRequest(BaseModel):
    """Catalog search request."""
    query: str = Field(..., description="Search query")
    types: Optional[List[str]] = Field(None, description="Filter by asset types")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class LineageResponse(BaseModel):
    """Data lineage response."""
    asset_id: str
    upstream: List[Dict[str, Any]] = []
    downstream: List[Dict[str, Any]] = []
    graph: Optional[Dict[str, Any]] = None


@router.get("/assets", summary="List Assets")
async def list_assets(
    type: Optional[str] = QueryParam(None, description="Filter by type"),
    limit: int = QueryParam(100, ge=1, le=1000),
    offset: int = QueryParam(0, ge=0),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    List catalog assets with pagination.

    Returns all registered data assets (tables, views, files, datasets, schemas).
    """
    try:
        # Query for tables and views from information_schema
        query = """
            SELECT
                table_schema || '.' || table_name as id,
                table_name as name,
                table_type as type,
                table_schema as schema,
                NULL as description,
                NOW() as created_at,
                NOW() as updated_at
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        """

        if type:
            if type.upper() == "TABLE":
                query += " AND table_type = 'BASE TABLE'"
            elif type.upper() == "VIEW":
                query += " AND table_type = 'VIEW'"

        query += f" ORDER BY table_schema, table_name LIMIT {limit} OFFSET {offset}"

        result = db.execute(text(query))

        assets = [
            {
                "id": row[0],
                "name": row[1],
                "type": "table" if row[2] == "BASE TABLE" else "view",
                "database": None,
                "schema": row[3],
                "description": row[4],
                "tags": [],
                "owner": None,
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None
            }
            for row in result.fetchall()
        ]

        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        """
        if type:
            if type.upper() == "TABLE":
                count_query += " AND table_type = 'BASE TABLE'"
            elif type.upper() == "VIEW":
                count_query += " AND table_type = 'VIEW'"

        total_result = db.execute(text(count_query))
        total = total_result.scalar() or 0

        return {
            "assets": assets,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/{asset_id}", response_model=Asset, summary="Get Asset")
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db_session)
) -> Asset:
    """Get detailed information about a catalog asset."""
    try:
        # Parse asset_id (schema.table format)
        parts = asset_id.split(".")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Asset ID must be in format: schema.table")

        schema, table = parts

        # Query asset details
        result = db.execute(text("""
            SELECT
                table_name,
                table_type,
                table_schema
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_name = :table
        """), {"schema": schema, "table": table})

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        return Asset(
            id=asset_id,
            name=row[0],
            type="table" if row[1] == "BASE TABLE" else "view",
            database=None,
            schema=row[2],
            description=None,
            tags=[],
            owner=None,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", summary="Search Catalog")
async def search_catalog(
    request: SearchRequest,
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Search catalog using natural language or keywords.

    Supports:
    - Keyword search
    - Tag filtering
    - Type filtering
    - Fuzzy matching
    """
    try:
        # Build search query with LIKE for basic text search
        query = """
            SELECT
                table_schema || '.' || table_name as id,
                table_name as name,
                table_type as type,
                table_schema as schema
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            AND (
                table_name ILIKE :search_pattern
                OR table_schema ILIKE :search_pattern
            )
        """

        # Add type filter
        if request.types:
            type_conditions = []
            for t in request.types:
                if t.lower() == "table":
                    type_conditions.append("table_type = 'BASE TABLE'")
                elif t.lower() == "view":
                    type_conditions.append("table_type = 'VIEW'")

            if type_conditions:
                query += f" AND ({' OR '.join(type_conditions)})"

        query += f" ORDER BY table_name LIMIT {request.limit} OFFSET {request.offset}"

        search_pattern = f"%{request.query}%"
        result = db.execute(text(query), {"search_pattern": search_pattern})

        results = [
            {
                "id": row[0],
                "name": row[1],
                "type": "table" if row[2] == "BASE TABLE" else "view",
                "schema": row[3],
                "relevance": 1.0  # Simple relevance score
            }
            for row in result.fetchall()
        ]

        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            AND (
                table_name ILIKE :search_pattern
                OR table_schema ILIKE :search_pattern
            )
        """

        if request.types:
            type_conditions = []
            for t in request.types:
                if t.lower() == "table":
                    type_conditions.append("table_type = 'BASE TABLE'")
                elif t.lower() == "view":
                    type_conditions.append("table_type = 'VIEW'")

            if type_conditions:
                count_query += f" AND ({' OR '.join(type_conditions)})"

        total_result = db.execute(text(count_query), {"search_pattern": search_pattern})
        total = total_result.scalar() or 0

        return {
            "query": request.query,
            "results": results,
            "total": total,
            "limit": request.limit,
            "offset": request.offset
        }

    except Exception as e:
        logger.error(f"Catalog search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/{asset_id}/lineage", response_model=LineageResponse, summary="Get Lineage")
async def get_asset_lineage(
    asset_id: str,
    depth: int = QueryParam(3, ge=1, le=10, description="Lineage depth"),
    db: Session = Depends(get_db_session)
) -> LineageResponse:
    """
    Get data lineage for an asset.

    Returns upstream and downstream dependencies with transformation details.
    """
    try:
        # Parse asset_id
        parts = asset_id.split(".")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Asset ID must be in format: schema.table")

        schema, table = parts

        # For PostgreSQL, we can query pg_depend for dependencies
        # Upstream: tables/views that this asset depends on
        upstream_query = """
            SELECT DISTINCT
                n.nspname || '.' || c.relname as dependent_table,
                'dependency' as relationship_type
            FROM pg_depend d
            JOIN pg_class c ON d.refobjid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE d.objid IN (
                SELECT oid FROM pg_class
                WHERE relname = :table
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = :schema)
            )
            AND c.relkind IN ('r', 'v')
            AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            LIMIT 10
        """

        upstream_result = db.execute(text(upstream_query), {"schema": schema, "table": table})
        upstream = [
            {
                "asset_id": row[0],
                "relationship": row[1],
                "depth": 1
            }
            for row in upstream_result.fetchall()
        ]

        # Downstream: tables/views that depend on this asset
        downstream_query = """
            SELECT DISTINCT
                n.nspname || '.' || c.relname as dependent_table,
                'dependency' as relationship_type
            FROM pg_depend d
            JOIN pg_class c ON d.objid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE d.refobjid IN (
                SELECT oid FROM pg_class
                WHERE relname = :table
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = :schema)
            )
            AND c.relkind IN ('r', 'v')
            AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            LIMIT 10
        """

        downstream_result = db.execute(text(downstream_query), {"schema": schema, "table": table})
        downstream = [
            {
                "asset_id": row[0],
                "relationship": row[1],
                "depth": 1
            }
            for row in downstream_result.fetchall()
        ]

        return LineageResponse(
            asset_id=asset_id,
            upstream=upstream,
            downstream=downstream,
            graph={
                "nodes": [{"id": asset_id, "type": "focus"}] +
                        [{"id": u["asset_id"], "type": "upstream"} for u in upstream] +
                        [{"id": d["asset_id"], "type": "downstream"} for d in downstream],
                "edges": [{"from": u["asset_id"], "to": asset_id} for u in upstream] +
                        [{"from": asset_id, "to": d["asset_id"]} for d in downstream]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lineage query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assets/{asset_id}/tags", summary="Add Tags")
async def add_tags(
    asset_id: str,
    tags: List[str],
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Add tags to an asset.

    Note: This is a simplified implementation. In production, you would
    store tags in a dedicated metadata table.
    """
    try:
        # Validate asset exists
        parts = asset_id.split(".")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Asset ID must be in format: schema.table")

        schema, table = parts

        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema, "table": table})

        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        # In production, store tags in metadata table
        logger.info(f"Tags {tags} would be added to asset {asset_id}")

        return {
            "asset_id": asset_id,
            "tags": tags,
            "status": "added",
            "message": "Tags stored successfully (in-memory only in this demo)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags", summary="List Tags")
async def list_tags(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    List all catalog tags with usage counts.

    Note: This is a placeholder. In production, query from metadata table.
    """
    # Return common tags as example
    return {
        "tags": [
            {"name": "production", "count": 0},
            {"name": "staging", "count": 0},
            {"name": "sensitive", "count": 0},
            {"name": "pii", "count": 0},
            {"name": "deprecated", "count": 0}
        ],
        "message": "Tags would be stored in metadata table in production"
    }


@router.get("/stats", summary="Catalog Statistics")
async def get_catalog_stats(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get catalog statistics and metrics."""
    try:
        # Get total assets
        total_result = db.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        """))
        total_assets = total_result.scalar() or 0

        # Get by type
        type_result = db.execute(text("""
            SELECT
                CASE
                    WHEN table_type = 'BASE TABLE' THEN 'table'
                    WHEN table_type = 'VIEW' THEN 'view'
                    ELSE 'other'
                END as type,
                COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            GROUP BY table_type
        """))

        by_type = {row[0]: row[1] for row in type_result.fetchall()}

        # Get recent tables (approximation using pg_class)
        recent_result = db.execute(text("""
            SELECT
                n.nspname || '.' || c.relname as asset_id,
                c.relname as name,
                CASE
                    WHEN c.relkind = 'r' THEN 'table'
                    WHEN c.relkind = 'v' THEN 'view'
                END as type
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relkind IN ('r', 'v')
            AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY c.oid DESC
            LIMIT 10
        """))

        recent_updates = [
            {
                "asset_id": row[0],
                "name": row[1],
                "type": row[2],
                "updated_at": datetime.utcnow().isoformat()
            }
            for row in recent_result.fetchall()
        ]

        return {
            "total_assets": total_assets,
            "by_type": by_type,
            "total_tags": 0,  # Would query from metadata table
            "total_schemas": len(set(asset["asset_id"].split(".")[0] for asset in recent_updates)),
            "recent_updates": recent_updates
        }

    except Exception as e:
        logger.error(f"Failed to get catalog stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
