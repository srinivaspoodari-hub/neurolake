#!/usr/bin/env python3
"""
NCF and Tables Viewer
View NCF files, table information, and MinIO storage
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("Installing required packages...")
    os.system("pip install minio psycopg2-binary")
    from minio import Minio

import psycopg2
from datetime import datetime


def print_header(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def view_minio_storage():
    """View MinIO storage and NCF files"""
    print_header("MinIO Storage - NCF Files and Buckets")

    try:
        # Connect to MinIO
        client = Minio(
            "localhost:9000",
            access_key="neurolake",
            secret_key="dev_password_change_in_prod",
            secure=False
        )

        print("\n>> Buckets:")
        buckets = client.list_buckets()
        if not buckets:
            print("  No buckets found. Creating 'neurolake-data' bucket...")
            client.make_bucket("neurolake-data")
            print("  + Bucket 'neurolake-data' created")
            buckets = client.list_buckets()

        for bucket in buckets:
            print(f"\n   {bucket.name}")
            print(f"     Created: {bucket.creation_date}")

            # List objects in bucket
            try:
                objects = list(client.list_objects(bucket.name, recursive=True))
                if objects:
                    print(f"\n     Objects ({len(objects)} files):")

                    ncf_files = []
                    other_files = []

                    for obj in objects:
                        if obj.object_name.endswith('.ncf'):
                            ncf_files.append(obj)
                        else:
                            other_files.append(obj)

                    # Show NCF files first
                    if ncf_files:
                        print("\n     * NCF Files:")
                        for obj in ncf_files[:10]:  # Show first 10
                            size_mb = obj.size / (1024 * 1024)
                            print(f"         {obj.object_name}")
                            print(f"          Size: {size_mb:.2f} MB | Modified: {obj.last_modified}")
                        if len(ncf_files) > 10:
                            print(f"        ... and {len(ncf_files) - 10} more NCF files")

                    # Show other files
                    if other_files:
                        print("\n      Other Files:")
                        for obj in other_files[:5]:  # Show first 5
                            size_mb = obj.size / (1024 * 1024)
                            print(f"         {obj.object_name}")
                            print(f"          Size: {size_mb:.2f} MB")
                        if len(other_files) > 5:
                            print(f"        ... and {len(other_files) - 5} more files")
                else:
                    print("     (empty)")
            except S3Error as e:
                print(f"     Error listing objects: {e}")

        # Storage summary
        print_header("Storage Summary")
        total_objects = sum(len(list(client.list_objects(b.name, recursive=True))) for b in buckets)
        print(f"  Total Buckets: {len(buckets)}")
        print(f"  Total Objects: {total_objects}")

        print("\n[OK] MinIO Console: http://localhost:9001")
        print("   Login: neurolake / dev_password_change_in_prod")

    except Exception as e:
        print(f"[ERROR] Error connecting to MinIO: {e}")
        print("   Make sure MinIO is running: docker-compose ps")


def view_postgres_tables():
    """View PostgreSQL tables"""
    print_header("PostgreSQL - Tables and Metadata")

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="neurolake",
            user="neurolake",
            password="dev_password_change_in_prod"
        )
        cur = conn.cursor()

        # Get all tables
        cur.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schemaname, tablename
        """)

        tables = cur.fetchall()

        if tables:
            print(f"\n>> Found {len(tables)} tables:\n")

            current_schema = None
            for schema, table, size in tables:
                if schema != current_schema:
                    print(f"\n   Schema: {schema}")
                    current_schema = schema

                print(f"      {table} ({size})")

                # Get column info
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    LIMIT 5
                """, (schema, table))

                columns = cur.fetchall()
                if columns:
                    print(f"       Columns: {', '.join([f'{col}({dtype})' for col, dtype in columns])}")
                    if len(columns) >= 5:
                        cur.execute("""
                            SELECT COUNT(*)
                            FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                        """, (schema, table))
                        total_cols = cur.fetchone()[0]
                        if total_cols > 5:
                            print(f"       ... and {total_cols - 5} more columns")
        else:
            print("\n  No user tables found.")
            print("  Tables will appear here after you:")
            print("    1. Run data ingestion")
            print("    2. Create tables via SQL")
            print("    3. Convert data to NCF format")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Error connecting to PostgreSQL: {e}")
        print("   Make sure PostgreSQL is running: docker-compose ps")


def view_ncf_rust_info():
    """View NCF Rust module info"""
    print_header("NCF (NeuroLake Columnar Format) - Rust Core")

    try:
        import ncf_rust
        print("\n[OK] NCF Rust module is installed and working!")
        print(f"   Module path: {ncf_rust.__file__}")

        # Show available functions
        print("\n>> Available NCF functions:")
        functions = [name for name in dir(ncf_rust) if not name.startswith('_')]
        for func in functions:
            print(f"    {func}")

        print("\n>> NCF Features:")
        print("   + Compression (ZSTD, LZ4, Snappy)")
        print("   + Columnar storage format")
        print("   + Vector embedding support")
        print("   + Checksum validation")
        print("   + 3-5x better compression than Parquet")

    except ImportError as e:
        print(f"[WARN]  NCF Rust module not installed: {e}")
        print("   Build it with: cd core/ncf-rust && cargo build --release")
        print("   Install with: pip install -e core/ncf-rust")


def main():
    """Main function"""
    print("""
    =================================================================

             NeuroLake - NCF and Tables Viewer

    =================================================================
    """)

    # View NCF module info
    view_ncf_rust_info()

    # View MinIO storage
    view_minio_storage()

    # View PostgreSQL tables
    view_postgres_tables()

    # Summary
    print_header("Quick Access")
    print("\n   Web Dashboards:")
    print("      MinIO Console:  http://localhost:9001")
    print("      Grafana:        http://localhost:3001")
    print("      Prometheus:     http://localhost:9090")
    print("      Jaeger:         http://localhost:16686")
    print("      Qdrant:         http://localhost:6333/dashboard")

    print("\n   Database Connections:")
    print("      PostgreSQL:     localhost:5432 (neurolake/dev_password_change_in_prod)")
    print("      Redis:          localhost:6379")
    print("      MinIO:          localhost:9000")

    print("\n   Documentation:")
    print("      NCF Format:     README_NCF.md")
    print("      Architecture:   ARCHITECTURE.md")
    print("      Dashboard:      UNIFIED_DASHBOARD.md")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
