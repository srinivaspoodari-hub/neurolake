"""
Data API Router (v1)

Data management endpoints for tables, schemas, and bulk operations.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from neurolake.db import get_db_session
from neurolake.engine import NeuroLakeEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class TableSchema(BaseModel):
    """Table schema information."""
    name: str
    database: str
    columns: List[Dict[str, Any]]
    row_count: int = 0
    size_bytes: int = 0


class BulkInsertRequest(BaseModel):
    """Bulk insert request."""
    table: str = Field(..., description="Target table name")
    data: List[Dict[str, Any]] = Field(..., description="Rows to insert")
    mode: str = Field("append", description="Insert mode: append, replace, upsert")


class BulkUpdateRequest(BaseModel):
    """Bulk update request."""
    table: str
    updates: List[Dict[str, Any]]
    where_clause: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    """Bulk delete request."""
    table: str
    ids: Optional[List[Any]] = None
    where_clause: Optional[str] = None


@router.get("/schemas", summary="List Schemas")
async def list_schemas(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """List all database schemas."""
    try:
        result = db.execute(text("""
            SELECT
                schema_name,
                (SELECT COUNT(*) FROM information_schema.tables
                 WHERE table_schema = schema_name AND table_type = 'BASE TABLE') as table_count,
                (SELECT COUNT(*) FROM information_schema.tables
                 WHERE table_schema = schema_name AND table_type = 'VIEW') as view_count
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """))

        schemas = [
            {
                "name": row[0],
                "table_count": row[1],
                "view_count": row[2]
            }
            for row in result.fetchall()
        ]

        return {"schemas": schemas}

    except Exception as e:
        logger.error(f"Failed to list schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", summary="List Tables")
async def list_tables(
    schema: str = "public",
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """List tables in a schema."""
    try:
        result = db.execute(text("""
            SELECT
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns
                 WHERE table_schema = :schema AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """), {"schema": schema})

        tables = [
            {
                "name": row[0],
                "column_count": row[1],
                "schema": schema
            }
            for row in result.fetchall()
        ]

        return {
            "schema": schema,
            "tables": tables,
            "count": len(tables)
        }

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/schema", response_model=TableSchema, summary="Get Table Schema")
async def get_table_schema(
    table_name: str,
    schema: str = "public",
    db: Session = Depends(get_db_session)
) -> TableSchema:
    """Get detailed schema for a table."""
    try:
        # Get column information
        result = db.execute(text("""
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema
            AND table_name = :table_name
            ORDER BY ordinal_position
        """), {"schema": schema, "table_name": table_name})

        columns = [
            {
                "name": row[0],
                "type": row[1],
                "max_length": row[2],
                "nullable": row[3] == "YES",
                "default": row[4]
            }
            for row in result.fetchall()
        ]

        if not columns:
            raise HTTPException(status_code=404, detail=f"Table {schema}.{table_name} not found")

        # Get row count
        count_result = db.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'))
        row_count = count_result.scalar() or 0

        # Get table size
        size_result = db.execute(text("""
            SELECT pg_total_relation_size(quote_ident(:schema) || '.' || quote_ident(:table_name))
        """), {"schema": schema, "table_name": table_name})
        size_bytes = size_result.scalar() or 0

        return TableSchema(
            name=table_name,
            database=schema,
            columns=columns,
            row_count=row_count,
            size_bytes=size_bytes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/preview", summary="Preview Table Data")
async def preview_table(
    table_name: str,
    schema: str = "public",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Preview table data with pagination."""
    try:
        engine = NeuroLakeEngine()

        # Get data using engine
        sql = f'SELECT * FROM "{schema}"."{table_name}" LIMIT {limit} OFFSET {offset}'
        result_df = engine.execute_sql(sql, return_format="dataframe")

        # Get total count
        count_result = db.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'))
        total_rows = count_result.scalar() or 0

        # Convert to response format
        if result_df is not None and not result_df.empty:
            data = result_df.to_dict('records')
            columns = result_df.columns.tolist()
        else:
            data = []
            columns = []

        return {
            "table": table_name,
            "schema": schema,
            "data": data,
            "columns": columns,
            "total_rows": total_rows,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to preview table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/insert", summary="Bulk Insert")
async def bulk_insert(
    request: BulkInsertRequest,
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Bulk insert rows into a table.

    Supports:
    - append: Add new rows
    - replace: Drop table and insert
    - upsert: Insert or update on conflict
    """
    try:
        if not request.data:
            raise HTTPException(status_code=400, detail="No data provided for insert")

        # Extract columns from first row
        columns = list(request.data[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        column_list = ", ".join([f'"{col}"' for col in columns])

        # Handle different modes
        if request.mode == "replace":
            # Truncate table first
            db.execute(text(f'TRUNCATE TABLE "{request.table}"'))
            logger.info(f"Truncated table {request.table}")

        # Build INSERT statement
        if request.mode == "upsert":
            # Assume first column is the key for simplicity
            key_column = columns[0]
            update_cols = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns[1:]])
            sql = f'''
                INSERT INTO "{request.table}" ({column_list})
                VALUES ({placeholders})
                ON CONFLICT ("{key_column}")
                DO UPDATE SET {update_cols}
            '''
        else:
            # Simple INSERT for append mode
            sql = f'INSERT INTO "{request.table}" ({column_list}) VALUES ({placeholders})'

        # Execute batch insert
        inserted = 0
        for row in request.data:
            db.execute(text(sql), row)
            inserted += 1

        db.commit()

        logger.info(f"Bulk insert: {inserted} rows into {request.table} (mode: {request.mode})")

        return {
            "table": request.table,
            "inserted": inserted,
            "mode": request.mode,
            "status": "success"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk insert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/update", summary="Bulk Update")
async def bulk_update(
    request: BulkUpdateRequest,
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Bulk update rows in a table."""
    try:
        if not request.updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        updated = 0

        for update in request.updates:
            # Assume first key is the ID field
            keys = list(update.keys())
            if not keys:
                continue

            id_field = keys[0]
            id_value = update[id_field]

            # Build SET clause
            set_clauses = [f'"{k}" = :{k}' for k in keys[1:]]
            set_clause = ", ".join(set_clauses)

            # Build WHERE clause
            if request.where_clause:
                where = request.where_clause
            else:
                where = f'"{id_field}" = :{id_field}'

            sql = f'UPDATE "{request.table}" SET {set_clause} WHERE {where}'

            result = db.execute(text(sql), update)
            updated += result.rowcount

        db.commit()

        logger.info(f"Bulk update: {updated} rows in {request.table}")

        return {
            "table": request.table,
            "updated": updated,
            "status": "success"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/delete", summary="Bulk Delete")
async def bulk_delete(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Bulk delete rows from a table."""
    try:
        if request.where_clause:
            # Use WHERE clause
            sql = f'DELETE FROM "{request.table}" WHERE {request.where_clause}'
            result = db.execute(text(sql))
            deleted = result.rowcount
        elif request.ids:
            # Delete by IDs (assume first column is ID)
            # Get first column name
            col_result = db.execute(text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :table
                ORDER BY ordinal_position
                LIMIT 1
            """), {"table": request.table})

            first_col = col_result.scalar()
            if not first_col:
                raise HTTPException(status_code=404, detail=f"Table {request.table} not found")

            # Build IN clause
            placeholders = ", ".join([f":id{i}" for i in range(len(request.ids))])
            sql = f'DELETE FROM "{request.table}" WHERE "{first_col}" IN ({placeholders})'

            # Create params dict
            params = {f"id{i}": id_val for i, id_val in enumerate(request.ids)}

            result = db.execute(text(sql), params)
            deleted = result.rowcount
        else:
            raise HTTPException(status_code=400, detail="Either ids or where_clause must be provided")

        db.commit()

        logger.info(f"Bulk delete: {deleted} rows from {request.table}")

        return {
            "table": request.table,
            "deleted": deleted,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", summary="Upload Data File")
async def upload_data_file(
    file: UploadFile = File(...),
    table: Optional[str] = None,
    schema: str = "public",
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Upload a data file (CSV, JSON, Parquet, NCF).

    Automatically detects file format and creates table if needed.
    """
    import tempfile
    import os
    import pandas as pd

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)

        # Determine file type
        filename = file.filename or "unknown"
        file_ext = os.path.splitext(filename)[1].lower()

        # Default table name if not provided
        if not table:
            table = os.path.splitext(filename)[0].replace(" ", "_").replace("-", "_")

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Read file based on extension
            if file_ext == ".csv":
                df = pd.read_csv(tmp_path)
            elif file_ext == ".json":
                df = pd.read_json(tmp_path)
            elif file_ext == ".parquet":
                df = pd.read_parquet(tmp_path)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {file_ext}. Supported: .csv, .json, .parquet"
                )

            rows_loaded = len(df)

            # Use NeuroLakeEngine to write data
            engine = NeuroLakeEngine()

            # For now, convert to SQL INSERT statements
            # In production, this should use COPY or bulk insert
            columns = df.columns.tolist()
            column_list = ", ".join([f'"{col}"' for col in columns])

            # Create table if doesn't exist (infer schema from DataFrame)
            type_mapping = {
                'int64': 'BIGINT',
                'float64': 'DOUBLE PRECISION',
                'object': 'TEXT',
                'bool': 'BOOLEAN',
                'datetime64[ns]': 'TIMESTAMP'
            }

            col_defs = [
                f'"{col}" {type_mapping.get(str(df[col].dtype), "TEXT")}'
                for col in columns
            ]
            create_sql = f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" ({", ".join(col_defs)})'

            db.execute(text(create_sql))
            db.commit()

            logger.info(f"Created/verified table {schema}.{table}")

            # Insert data
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f'INSERT INTO "{schema}"."{table}" ({column_list}) VALUES ({placeholders})'

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                db.execute(text(insert_sql), row_dict)

            db.commit()

            logger.info(f"Loaded {rows_loaded} rows into {schema}.{table} from {filename}")

            return {
                "filename": filename,
                "content_type": file.content_type,
                "size_bytes": file_size,
                "table": f"{schema}.{table}",
                "rows_loaded": rows_loaded,
                "columns": columns,
                "status": "success"
            }

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
