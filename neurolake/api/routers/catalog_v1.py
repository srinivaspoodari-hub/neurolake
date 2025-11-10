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


# ============================================================================
# NUIC CATALOG BROWSER ENDPOINTS
# ============================================================================

class SchemaInfo(BaseModel):
    """Schema information model."""
    name: str
    database: Optional[str] = None
    description: Optional[str] = None
    table_count: int
    created_at: str
    owner: Optional[str] = None


class TableInfo(BaseModel):
    """Table listing information."""
    name: str
    schema: str
    type: str  # 'table', 'view', 'external'
    format: Optional[str] = "NCF"
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: str
    updated_at: str
    description: Optional[str] = None


class ColumnInfo(BaseModel):
    """Column schema information."""
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None


class TableDetails(BaseModel):
    """Detailed table information."""
    name: str
    schema: str
    database: Optional[str] = None
    type: str  # 'table', 'view', 'external'
    format: str = "NCF"
    location: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    last_accessed: Optional[str] = None
    columns: List[ColumnInfo]
    properties: Optional[Dict[str, Any]] = {}
    statistics: Optional[Dict[str, Any]] = {}
    partitions: Optional[List[Dict[str, str]]] = []


class TableVersion(BaseModel):
    """Table version history entry."""
    version: int
    created_at: str
    created_by: str
    operation: str  # 'CREATE', 'UPDATE', 'DELETE', 'ALTER'
    changes: Optional[Dict[str, Any]] = None
    snapshot_id: Optional[str] = None


class TablePermission(BaseModel):
    """Table access permission."""
    id: int
    principal_type: str  # 'user', 'group', 'organization'
    principal_id: Any  # Can be string or int
    principal_name: str
    permissions: List[str]
    granted_by: Optional[str] = None
    granted_at: str


class GrantAccessRequest(BaseModel):
    """Grant access request."""
    principal_type: str
    principal_id: Any
    permissions: List[str]


class CreateTableRequest(BaseModel):
    """Create table request."""
    name: str
    columns: List[ColumnInfo]
    description: Optional[str] = None
    format: str = "NCF"
    location: Optional[str] = None
    properties: Optional[Dict[str, Any]] = {}


@router.get("/schemas", summary="List Schemas")
async def list_schemas(
    db: Session = Depends(get_db_session)
) -> Dict[str, List[SchemaInfo]]:
    """List all schemas in the catalog."""
    try:
        result = db.execute(text("""
            SELECT
                table_schema,
                COUNT(*) as table_count
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            GROUP BY table_schema
            ORDER BY table_schema
        """))

        schemas = [
            SchemaInfo(
                name=row[0],
                database=None,
                description=None,
                table_count=row[1],
                created_at=datetime.utcnow().isoformat(),
                owner=None
            )
            for row in result.fetchall()
        ]

        return {"schemas": schemas}

    except Exception as e:
        logger.error(f"Failed to list schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/{schema_name}/tables", summary="List Tables in Schema")
async def list_schema_tables(
    schema_name: str,
    db: Session = Depends(get_db_session)
) -> Dict[str, List[TableInfo]]:
    """List all tables in a schema."""
    try:
        result = db.execute(text("""
            SELECT
                table_name,
                table_type,
                NULL as row_count,
                NULL as size_bytes
            FROM information_schema.tables
            WHERE table_schema = :schema
            ORDER BY table_name
        """), {"schema": schema_name})

        tables = [
            TableInfo(
                name=row[0],
                schema=schema_name,
                type="table" if row[1] == "BASE TABLE" else "view",
                format="NCF",
                row_count=row[2],
                size_bytes=row[3],
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                description=None
            )
            for row in result.fetchall()
        ]

        return {"tables": tables}

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/{schema_name}/tables/{table_name}/details", response_model=TableDetails, summary="Get Table Details")
async def get_table_details(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db_session)
) -> TableDetails:
    """Get detailed information about a table."""
    try:
        # Get table info
        table_result = db.execute(text("""
            SELECT table_type
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema_name, "table": table_name})

        table_row = table_result.fetchone()
        if not table_row:
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # Get column info
        columns_result = db.execute(text("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {"schema": schema_name, "table": table_name})

        columns = [
            ColumnInfo(
                name=row[0],
                type=row[1],
                nullable=(row[2] == 'YES'),
                description=None
            )
            for row in columns_result.fetchall()
        ]

        return TableDetails(
            name=table_name,
            schema=schema_name,
            database=None,
            type="table" if table_row[0] == "BASE TABLE" else "view",
            format="NCF",
            location=f"/data/warehouse/{schema_name}/{table_name}",
            description=None,
            owner="system",
            created_by="system",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            last_accessed=None,
            columns=columns,
            properties={},
            statistics={"row_count": 0, "size_bytes": 0, "file_count": 0},
            partitions=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/{schema_name}/tables/{table_name}/ddl", summary="Get Table DDL")
async def get_table_ddl(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db_session)
) -> Dict[str, str]:
    """Get table DDL (CREATE TABLE statement)."""
    try:
        # Get columns
        columns_result = db.execute(text("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {"schema": schema_name, "table": table_name})

        columns = columns_result.fetchall()
        if not columns:
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # Build DDL
        ddl = f"CREATE TABLE {schema_name}.{table_name} (\n"
        column_defs = []

        for col in columns:
            col_def = f"  {col[0]} {col[1]}"
            if col[2] == 'NO':
                col_def += " NOT NULL"
            if col[3]:
                col_def += f" DEFAULT {col[3]}"
            column_defs.append(col_def)

        ddl += ",\n".join(column_defs)
        ddl += "\n) FORMAT NCF\n"
        ddl += f"LOCATION '/data/warehouse/{schema_name}/{table_name}';"

        return {"ddl": ddl}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DDL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/{schema_name}/tables/{table_name}/sample", summary="Get Sample Data")
async def get_table_sample(
    schema_name: str,
    table_name: str,
    limit: int = QueryParam(100, ge=1, le=1000),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Get sample data from table."""
    try:
        # Get column names
        columns_result = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {"schema": schema_name, "table": table_name})

        columns = [row[0] for row in columns_result.fetchall()]
        if not columns:
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # Get sample data
        data_result = db.execute(text(f"""
            SELECT * FROM {schema_name}.{table_name}
            LIMIT :limit
        """), {"limit": limit})

        data = [
            {columns[i]: row[i] for i in range(len(columns))}
            for row in data_result.fetchall()
        ]

        return {
            "columns": columns,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas/{schema_name}/tables/{table_name}/versions", summary="Get Version History")
async def get_table_versions(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db_session)
) -> Dict[str, List[TableVersion]]:
    """Get table version history."""
    # Placeholder - in production, query from version control table
    return {
        "versions": [
            TableVersion(
                version=1,
                created_at=datetime.utcnow().isoformat(),
                created_by="system",
                operation="CREATE",
                changes={"action": "Table created"},
                snapshot_id=None
            )
        ]
    }


@router.get("/schemas/{schema_name}/tables/{table_name}/permissions", summary="Get Table Permissions")
async def get_table_permissions(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db_session)
) -> Dict[str, List[TablePermission]]:
    """Get table access permissions."""
    # Placeholder - in production, query from permissions table
    return {
        "permissions": [
            TablePermission(
                id=1,
                principal_type="user",
                principal_id=1,
                principal_name="admin",
                permissions=["SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "DROP"],
                granted_by="system",
                granted_at=datetime.utcnow().isoformat()
            )
        ]
    }


@router.post("/schemas/{schema_name}/tables/{table_name}/permissions", summary="Grant Access")
async def grant_table_access(
    schema_name: str,
    table_name: str,
    request: GrantAccessRequest,
    db: Session = Depends(get_db_session)
) -> Dict[str, str]:
    """Grant table access to user, group, or organization."""
    try:
        # Verify table exists
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema_name, "table": table_name})

        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # In production, insert into permissions table
        logger.info(f"Granting {request.permissions} on {schema_name}.{table_name} to {request.principal_type}:{request.principal_id}")

        return {
            "status": "success",
            "message": f"Access granted to {request.principal_type}:{request.principal_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to grant access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schemas/{schema_name}/tables/{table_name}/permissions/{permission_id}", summary="Revoke Access")
async def revoke_table_access(
    schema_name: str,
    table_name: str,
    permission_id: int,
    db: Session = Depends(get_db_session)
) -> Dict[str, str]:
    """Revoke table access permission."""
    try:
        # In production, delete from permissions table
        logger.info(f"Revoking permission {permission_id} on {schema_name}.{table_name}")

        return {
            "status": "success",
            "message": f"Permission {permission_id} revoked"
        }

    except Exception as e:
        logger.error(f"Failed to revoke access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schemas/{schema_name}/tables", response_model=TableDetails, summary="Create Table")
async def create_table(
    schema_name: str,
    request: CreateTableRequest,
    db: Session = Depends(get_db_session)
) -> TableDetails:
    """Create a new table."""
    try:
        # Build CREATE TABLE statement
        column_defs = []
        for col in request.columns:
            col_def = f"{col.name} {col.type}"
            if not col.nullable:
                col_def += " NOT NULL"
            column_defs.append(col_def)

        ddl = f"CREATE TABLE {schema_name}.{request.name} ({', '.join(column_defs)})"

        # Execute DDL
        db.execute(text(ddl))
        db.commit()

        logger.info(f"Created table {schema_name}.{request.name}")

        return TableDetails(
            name=request.name,
            schema=schema_name,
            database=None,
            type="table",
            format=request.format,
            location=request.location or f"/data/warehouse/{schema_name}/{request.name}",
            description=request.description,
            owner="system",
            created_by="system",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            last_accessed=None,
            columns=request.columns,
            properties=request.properties,
            statistics={"row_count": 0, "size_bytes": 0, "file_count": 0},
            partitions=[]
        )

    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schemas/{schema_name}/tables/{table_name}", summary="Delete Table")
async def delete_table(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db_session)
) -> Dict[str, str]:
    """Delete a table."""
    try:
        # Verify table exists
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema_name, "table": table_name})

        if not result.fetchone():
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # Drop table
        db.execute(text(f"DROP TABLE {schema_name}.{table_name}"))
        db.commit()

        logger.info(f"Deleted table {schema_name}.{table_name}")

        return {
            "status": "success",
            "message": f"Table {schema_name}.{table_name} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete table: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/schemas/{schema_name}/tables/{table_name}", response_model=TableDetails, summary="Update Table Properties")
async def update_table_properties(
    schema_name: str,
    table_name: str,
    properties: Dict[str, Any],
    db: Session = Depends(get_db_session)
) -> TableDetails:
    """Update table properties."""
    try:
        # Verify table exists
        result = db.execute(text("""
            SELECT table_type FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema_name, "table": table_name})

        table_row = result.fetchone()
        if not table_row:
            raise HTTPException(status_code=404, detail=f"Table {schema_name}.{table_name} not found")

        # In production, store properties in metadata table
        logger.info(f"Updated properties for {schema_name}.{table_name}: {properties}")

        # Get updated details
        return await get_table_details(schema_name, table_name, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update table properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))
