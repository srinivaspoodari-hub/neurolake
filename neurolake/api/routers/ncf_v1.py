"""
NCF API Router (v1)

API endpoints for NeuroLake Columnar Format (NCF) table operations.
Provides access to NCF storage manager features including time travel,
MERGE/UPSERT, OPTIMIZE, and schema operations.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from neurolake.db import get_db_session
from neurolake.storage.manager import NCFStorageManager

logger = logging.getLogger(__name__)
router = APIRouter()


# ===== Request/Response Models =====

class TableCreateRequest(BaseModel):
    """Request to create NCF table."""
    name: str = Field(..., description="Table name")
    schema: Dict[str, str] = Field(..., description="Column name to type mapping")
    partition_by: Optional[List[str]] = Field(None, description="Partition columns")
    description: str = Field("", description="Table description")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class TableWriteRequest(BaseModel):
    """Request to write data to NCF table."""
    data: List[Dict[str, Any]] = Field(..., description="Rows to write")
    mode: str = Field("append", description="Write mode: append, overwrite, error, ignore")


class TableMergeRequest(BaseModel):
    """Request to merge/upsert data."""
    data: List[Dict[str, Any]] = Field(..., description="Rows to merge")
    on: List[str] = Field(..., description="Key columns for merge")
    update_cols: Optional[List[str]] = Field(None, description="Columns to update (None = all)")


class TableOptimizeRequest(BaseModel):
    """Request to optimize table."""
    z_order_by: Optional[List[str]] = Field(None, description="Columns for z-ordering")
    compact_small_files: bool = Field(True, description="Compact small files")


class TableVacuumRequest(BaseModel):
    """Request to vacuum table."""
    retention_hours: int = Field(168, description="Retain versions newer than this (hours)", ge=0)


# ===== Storage Manager Dependency =====

def get_storage_manager() -> NCFStorageManager:
    """Get NCF storage manager instance."""
    # TODO: Get base path from settings
    return NCFStorageManager(base_path="./data/ncf")


# ===== Table Management Endpoints =====

@router.get("/tables", summary="List NCF Tables")
async def list_tables(
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    List all NCF tables.

    Returns table names, locations, and basic metadata.
    """
    try:
        tables = storage.list_tables()

        return {
            "tables": [
                {
                    "name": table.name,
                    "location": table.location,
                    "format": table.format,
                    "version": table.version,
                    "created_at": table.created_at.isoformat() if table.created_at else None,
                    "updated_at": table.updated_at.isoformat() if table.updated_at else None,
                    "row_count": table.statistics.row_count if table.statistics else 0,
                    "partition_columns": table.partition_columns
                }
                for table in tables
            ],
            "count": len(tables)
        }

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables", summary="Create NCF Table")
async def create_table(
    request: TableCreateRequest,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Create a new NCF table.

    The table will be automatically registered in the NUIC catalog.
    """
    try:
        metadata = storage.create_table(
            table_name=request.name,
            schema=request.schema,
            partition_by=request.partition_by,
            description=request.description,
            properties=request.properties
        )

        return {
            "name": metadata.name,
            "location": metadata.location,
            "schema": metadata.schema,
            "partition_columns": metadata.partition_columns,
            "created_at": metadata.created_at.isoformat(),
            "version": metadata.version,
            "status": "created",
            "message": "Table created and cataloged in NUIC"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}", summary="Get Table Metadata")
async def get_table(
    table_name: str,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Get detailed metadata for an NCF table."""
    try:
        metadata = storage.get_table_metadata(table_name)

        return {
            "name": metadata.name,
            "location": metadata.location,
            "schema": metadata.schema,
            "partition_columns": metadata.partition_columns,
            "description": metadata.description,
            "properties": metadata.properties,
            "format": metadata.format,
            "version": metadata.version,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
            "statistics": {
                "row_count": metadata.statistics.row_count,
                "size_bytes": metadata.statistics.size_bytes,
                "num_files": metadata.statistics.num_files
            } if metadata.statistics else None
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get table metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tables/{table_name}", summary="Drop Table")
async def drop_table(
    table_name: str,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Drop an NCF table and all its data."""
    try:
        storage.drop_table(table_name)

        return {
            "table": table_name,
            "status": "dropped",
            "message": f"Table '{table_name}' has been dropped"
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to drop table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Data Operations =====

@router.post("/tables/{table_name}/write", summary="Write Data")
async def write_data(
    table_name: str,
    request: TableWriteRequest,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Write data to NCF table.

    Supports modes: append, overwrite, error, ignore
    """
    try:
        # Convert list of dicts to dict of lists (columnar format)
        columnar_data = {}
        if request.data:
            for key in request.data[0].keys():
                columnar_data[key] = [row[key] for row in request.data]

        history = storage.write_table(
            table_name=table_name,
            data=columnar_data,
            mode=request.mode
        )

        return {
            "table": table_name,
            "rows_written": len(request.data),
            "mode": request.mode,
            "version": history.version,
            "timestamp": history.timestamp.isoformat(),
            "status": "success"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to write data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/read", summary="Read Data")
async def read_data(
    table_name: str,
    version: Optional[int] = QueryParam(None, description="Specific version (for time travel)"),
    timestamp: Optional[str] = QueryParam(None, description="ISO timestamp (for time travel)"),
    limit: int = QueryParam(1000, ge=1, le=100000, description="Max rows to return"),
    offset: int = QueryParam(0, ge=0, description="Rows to skip"),
    columns: Optional[str] = QueryParam(None, description="Comma-separated column names"),
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Read data from NCF table.

    Supports time travel via version or timestamp.
    """
    try:
        # Time travel
        if version is not None:
            df = storage.read_at_version(table_name, version)
        elif timestamp is not None:
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            df = storage.read_at_timestamp(table_name, ts)
        else:
            df = storage.read_table(table_name)

        # Column selection
        if columns:
            col_list = [c.strip() for c in columns.split(',')]
            df = df[col_list]

        # Pagination
        total_rows = len(df)
        df = df.iloc[offset:offset+limit]

        return {
            "table": table_name,
            "columns": df.columns.tolist(),
            "data": df.to_dict('records'),
            "row_count": len(df),
            "total_rows": total_rows,
            "limit": limit,
            "offset": offset,
            "version": version,
            "timestamp": timestamp
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to read data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables/{table_name}/merge", summary="Merge/Upsert Data")
async def merge_data(
    table_name: str,
    request: TableMergeRequest,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    MERGE/UPSERT data into NCF table.

    Updates existing rows based on key columns, inserts new rows.
    """
    try:
        # Convert list of dicts to dict of lists
        columnar_data = {}
        if request.data:
            for key in request.data[0].keys():
                columnar_data[key] = [row[key] for row in request.data]

        history = storage.merge(
            table_name=table_name,
            data=columnar_data,
            on=request.on,
            update_cols=request.update_cols
        )

        return {
            "table": table_name,
            "rows_merged": len(request.data),
            "merge_keys": request.on,
            "version": history.version,
            "timestamp": history.timestamp.isoformat(),
            "status": "success"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to merge data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Time Travel =====

@router.get("/tables/{table_name}/versions", summary="List Table Versions")
async def list_versions(
    table_name: str,
    limit: int = QueryParam(100, ge=1, le=1000),
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    List all versions of a table for time travel.

    Returns version history with timestamps and operations.
    """
    try:
        history = storage.get_history(table_name)

        versions = [
            {
                "version": h.version,
                "timestamp": h.timestamp.isoformat(),
                "operation": h.operation,
                "operation_params": h.operation_params,
                "username": h.username
            }
            for h in history[:limit]
        ]

        return {
            "table": table_name,
            "versions": versions,
            "total": len(history),
            "limit": limit
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/time-travel", summary="Time Travel Query")
async def time_travel(
    table_name: str,
    version: Optional[int] = QueryParam(None, description="Specific version number"),
    timestamp: Optional[str] = QueryParam(None, description="ISO timestamp"),
    limit: int = QueryParam(1000, ge=1, le=100000),
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Read NCF table at a specific version or timestamp.

    Examples:
        GET /api/ncf/tables/users/time-travel?version=5
        GET /api/ncf/tables/users/time-travel?timestamp=2025-01-01T00:00:00Z
    """
    try:
        if version is not None:
            df = storage.read_at_version(table_name, version, limit=limit)
            mode = "version"
            identifier = version
        elif timestamp is not None:
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            df = storage.read_at_timestamp(table_name, ts, limit=limit)
            mode = "timestamp"
            identifier = timestamp
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'version' or 'timestamp' parameter"
            )

        return {
            "table": table_name,
            "mode": mode,
            [mode]: identifier,
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "data": df.to_dict('records')
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Time travel query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Schema Operations =====

@router.get("/tables/{table_name}/schema", summary="Get Table Schema")
async def get_schema(
    table_name: str,
    version: Optional[int] = QueryParam(None, description="Schema at specific version"),
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Get table schema, optionally at a specific version."""
    try:
        metadata = storage.get_table_metadata(table_name)

        # TODO: Support schema at specific version
        if version is not None:
            logger.warning(f"Schema versioning not yet implemented, returning current schema")

        return {
            "table": table_name,
            "schema": metadata.schema,
            "partition_columns": metadata.partition_columns,
            "version": metadata.version
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Optimization Operations =====

@router.post("/tables/{table_name}/optimize", summary="Optimize Table")
async def optimize_table(
    table_name: str,
    request: TableOptimizeRequest,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Optimize NCF table.

    Performs:
    - File compaction (merge small files)
    - Z-ordering (optional, if columns specified)
    - Statistics updates
    """
    try:
        result = storage.optimize(
            table_name=table_name,
            z_order_by=request.z_order_by,
            compact_small_files=request.compact_small_files
        )

        return {
            "table": table_name,
            "status": "optimized",
            "z_order_by": request.z_order_by,
            "files_compacted": result.get("files_compacted", 0),
            "bytes_saved": result.get("bytes_saved", 0),
            "duration_ms": result.get("duration_ms", 0)
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to optimize table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables/{table_name}/vacuum", summary="Vacuum Table")
async def vacuum_table(
    table_name: str,
    request: TableVacuumRequest,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    VACUUM table to remove old versions.

    Deletes data files for versions older than retention period.
    Default retention: 168 hours (7 days).
    """
    try:
        result = storage.vacuum(
            table_name=table_name,
            retention_hours=request.retention_hours
        )

        return {
            "table": table_name,
            "status": "vacuumed",
            "retention_hours": request.retention_hours,
            "versions_removed": result.get("versions_removed", 0),
            "files_deleted": result.get("files_deleted", 0),
            "bytes_freed": result.get("bytes_freed", 0)
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to vacuum table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Statistics =====

@router.get("/tables/{table_name}/stats", summary="Get Table Statistics")
async def get_stats(
    table_name: str,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Get detailed statistics for NCF table."""
    try:
        metadata = storage.get_table_metadata(table_name)
        stats = metadata.statistics

        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")

        return {
            "table": table_name,
            "row_count": stats.row_count,
            "size_bytes": stats.size_bytes,
            "size_mb": stats.size_bytes / (1024 * 1024),
            "num_files": stats.num_files,
            "num_partitions": stats.num_partitions,
            "column_stats": stats.column_stats,
            "computed_at": stats.computed_at.isoformat() if stats.computed_at else None
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Column-Level Statistics =====

@router.get("/tables/{table_name}/columns", summary="List Table Columns")
async def list_columns(
    table_name: str,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    List all columns in NCF table with basic metadata.

    Returns column names, types, and whether they're nullable.
    """
    try:
        metadata = storage.get_metadata(table_name)

        columns = []
        for col_name, col_type in metadata.schema.items():
            columns.append({
                "name": col_name,
                "type": col_type,
                "nullable": True  # NCF supports nulls by default
            })

        return {
            "table": table_name,
            "column_count": len(columns),
            "columns": columns
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to list columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/columns/{column_name}/stats", summary="Get Column Statistics")
async def get_column_stats(
    table_name: str,
    column_name: str,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific column.

    Returns min, max, null count, distinct count, and data type info.
    """
    try:
        import pandas as pd

        # Read table data and convert to DataFrame
        data = storage.read_table(table_name)
        df = pd.DataFrame(data)

        if column_name not in df.columns:
            raise HTTPException(
                status_code=404,
                detail=f"Column '{column_name}' not found in table '{table_name}'"
            )

        column = df[column_name]

        # Calculate statistics
        stats = {
            "table": table_name,
            "column": column_name,
            "type": str(column.dtype),
            "total_count": len(column),
            "null_count": int(column.isnull().sum()),
            "non_null_count": int(column.notnull().sum()),
            "null_percentage": float(column.isnull().sum() / len(column) * 100) if len(column) > 0 else 0.0
        }

        # Add numeric statistics if numeric column
        if column.dtype.kind in ['i', 'f', 'u']:  # integer, float, unsigned
            stats.update({
                "min": float(column.min()) if not column.isnull().all() else None,
                "max": float(column.max()) if not column.isnull().all() else None,
                "mean": float(column.mean()) if not column.isnull().all() else None,
                "median": float(column.median()) if not column.isnull().all() else None,
                "std": float(column.std()) if not column.isnull().all() else None,
                "sum": float(column.sum()) if not column.isnull().all() else None
            })

        # Add string statistics if string column
        elif column.dtype == 'object' or str(column.dtype) == 'string':
            non_null = column.dropna()
            if len(non_null) > 0:
                stats.update({
                    "min_length": int(non_null.astype(str).str.len().min()),
                    "max_length": int(non_null.astype(str).str.len().max()),
                    "avg_length": float(non_null.astype(str).str.len().mean())
                })

        # Add distinct count for all types
        stats["distinct_count"] = int(column.nunique())
        stats["distinct_percentage"] = float(column.nunique() / len(column) * 100) if len(column) > 0 else 0.0

        return stats

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get column statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/columns/{column_name}/histogram", summary="Get Column Histogram")
async def get_column_histogram(
    table_name: str,
    column_name: str,
    bins: int = 10,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Get histogram data for a numeric column.

    Args:
        bins: Number of histogram bins (default: 10, max: 100)

    Returns histogram with bin edges and counts.
    """
    try:
        import pandas as pd

        # Validate bins
        if bins < 1 or bins > 100:
            raise HTTPException(
                status_code=400,
                detail="Bins must be between 1 and 100"
            )

        # Read table data and convert to DataFrame
        data = storage.read_table(table_name)
        df = pd.DataFrame(data)

        if column_name not in df.columns:
            raise HTTPException(
                status_code=404,
                detail=f"Column '{column_name}' not found in table '{table_name}'"
            )

        column = df[column_name].dropna()

        # Check if numeric
        if column.dtype.kind not in ['i', 'f', 'u']:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{column_name}' is not numeric (type: {column.dtype})"
            )

        if len(column) == 0:
            return {
                "table": table_name,
                "column": column_name,
                "bins": [],
                "counts": [],
                "total_count": 0
            }

        # Calculate histogram using pandas
        import numpy as np
        counts, bin_edges = np.histogram(column, bins=bins)

        # Format bins as ranges
        histogram_bins = []
        for i in range(len(counts)):
            histogram_bins.append({
                "min": float(bin_edges[i]),
                "max": float(bin_edges[i + 1]),
                "count": int(counts[i]),
                "percentage": float(counts[i] / len(column) * 100)
            })

        return {
            "table": table_name,
            "column": column_name,
            "total_count": len(column),
            "bins": histogram_bins,
            "min_value": float(column.min()),
            "max_value": float(column.max())
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get histogram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/columns/{column_name}/distinct-values", summary="Get Distinct Values")
async def get_distinct_values(
    table_name: str,
    column_name: str,
    limit: int = 100,
    storage: NCFStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """
    Get distinct values and their counts for a column.

    Args:
        limit: Maximum number of distinct values to return (default: 100, max: 1000)

    Returns top distinct values with counts, ordered by frequency.
    """
    try:
        import pandas as pd

        # Validate limit
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000"
            )

        # Read table data and convert to DataFrame
        data = storage.read_table(table_name)
        df = pd.DataFrame(data)

        if column_name not in df.columns:
            raise HTTPException(
                status_code=404,
                detail=f"Column '{column_name}' not found in table '{table_name}'"
            )

        column = df[column_name]

        # Get value counts (top N)
        value_counts = column.value_counts().head(limit)

        # Format results
        distinct_values = []
        for value, count in value_counts.items():
            # Handle different types
            if isinstance(value, (int, float, bool)):
                formatted_value = value
            elif value is None or (isinstance(value, float) and np.isnan(value)):
                formatted_value = None
            else:
                formatted_value = str(value)

            distinct_values.append({
                "value": formatted_value,
                "count": int(count),
                "percentage": float(count / len(column) * 100)
            })

        return {
            "table": table_name,
            "column": column_name,
            "total_rows": len(column),
            "total_distinct": int(column.nunique()),
            "null_count": int(column.isnull().sum()),
            "showing_top": len(distinct_values),
            "values": distinct_values
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get distinct values: {e}")
        raise HTTPException(status_code=500, detail=str(e))
