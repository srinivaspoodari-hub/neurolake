"""
Populate NeuroLake Local Storage with Sample Catalog Data
"""
import sys
import os

# Add the project root to the path so we can import catalog modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neurolake.catalog.data_catalog import DataCatalog
from neurolake.catalog.lineage_tracker import LineageTracker
from neurolake.catalog.schema_registry import SchemaRegistry

def populate_neurolake_catalog():
    """Populate NeuroLake catalog at C:/NeuroLake/catalog with sample data for dashboard testing"""

    print("=" * 80)
    print("Populating NeuroLake Local Storage with Sample Catalog Data".center(80))
    print("=" * 80)
    print()

    # Initialize catalog with NeuroLake local storage paths
    catalog_path = "C:/NeuroLake/catalog"
    lineage_path = "C:/NeuroLake/catalog"
    schema_path = "C:/NeuroLake/catalog"

    print(f"Catalog Path: {catalog_path}")
    print()

    # Initialize modules
    print("[STEP 1] Initializing Catalog Modules")
    print("-" * 80)

    catalog = DataCatalog(storage_path=catalog_path)
    lineage = LineageTracker(storage_path=lineage_path)
    schema_registry = SchemaRegistry(storage_path=schema_path)

    print("  [OK] DataCatalog initialized")
    print("  [OK] LineageTracker initialized")
    print("  [OK] SchemaRegistry initialized")

    # Register sample tables
    print()
    print("[STEP 2] Registering Sample Tables")
    print("-" * 80)

    # Table 1: customers
    customers_id = catalog.register_table(
        table_name='customers',
        database='production',
        schema='public',
        columns=[
            {'name': 'customer_id', 'type': 'int'},
            {'name': 'email', 'type': 'string'},
            {'name': 'first_name', 'type': 'string'},
            {'name': 'last_name', 'type': 'string'},
            {'name': 'created_at', 'type': 'timestamp'}
        ],
        description='Customer master data table with PII',
        tags=['production', 'pii', 'master-data']
    )
    print(f"  [OK] Registered: production.public.customers ({customers_id})")

    # Table 2: orders
    orders_id = catalog.register_table(
        table_name='orders',
        database='production',
        schema='public',
        columns=[
            {'name': 'order_id', 'type': 'int'},
            {'name': 'customer_id', 'type': 'int'},
            {'name': 'total_amount', 'type': 'decimal'},
            {'name': 'order_date', 'type': 'timestamp'},
            {'name': 'status', 'type': 'string'}
        ],
        description='Order transactions table',
        tags=['production', 'transactional']
    )
    print(f"  [OK] Registered: production.public.orders ({orders_id})")

    # Table 3: products
    products_id = catalog.register_table(
        table_name='products',
        database='production',
        schema='public',
        columns=[
            {'name': 'product_id', 'type': 'int'},
            {'name': 'product_name', 'type': 'string'},
            {'name': 'category', 'type': 'string'},
            {'name': 'price', 'type': 'decimal'}
        ],
        description='Product catalog table',
        tags=['production', 'catalog', 'master-data']
    )
    print(f"  [OK] Registered: production.public.products ({products_id})")

    # Table 4: customer_summary (analytics)
    customer_summary_id = catalog.register_table(
        table_name='customer_summary',
        database='analytics',
        schema='reporting',
        columns=[
            {'name': 'customer_id', 'type': 'int'},
            {'name': 'total_orders', 'type': 'int'},
            {'name': 'total_revenue', 'type': 'decimal'},
            {'name': 'last_order_date', 'type': 'timestamp'}
        ],
        description='Customer analytics summary table',
        tags=['analytics', 'aggregated', 'reporting']
    )
    print(f"  [OK] Registered: analytics.reporting.customer_summary ({customer_summary_id})")

    # Table 5: customer_features (ML)
    customer_features_id = catalog.register_table(
        table_name='customer_features',
        database='ml',
        schema='features',
        columns=[
            {'name': 'customer_id', 'type': 'int'},
            {'name': 'churn_risk', 'type': 'float'},
            {'name': 'lifetime_value', 'type': 'float'},
            {'name': 'segment', 'type': 'string'}
        ],
        description='ML features for customer predictions',
        tags=['ml', 'features', 'predictions']
    )
    print(f"  [OK] Registered: ml.features.customer_features ({customer_features_id})")

    # Register lineage
    print()
    print("[STEP 3] Creating Data Lineage")
    print("-" * 80)

    # Lineage 1: customer_summary derived from customers and orders
    lineage.track_query_lineage(
        query_id='query_customer_summary',
        input_tables=['production.public.customers', 'production.public.orders'],
        output_table='analytics.reporting.customer_summary',
        query_text="""
            SELECT
                c.customer_id,
                COUNT(o.order_id) as total_orders,
                SUM(o.total_amount) as total_revenue,
                MAX(o.order_date) as last_order_date
            FROM production.public.customers c
            LEFT JOIN production.public.orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id
        """,
        column_mapping={
            'customer_id': ['customers.customer_id'],
            'total_orders': ['orders.order_id'],
            'total_revenue': ['orders.total_amount'],
            'last_order_date': ['orders.order_date']
        }
    )
    print("  [OK] Tracked lineage: customer_summary <- customers + orders")

    # Lineage 2: customer_features derived from customer_summary
    lineage.track_query_lineage(
        query_id='query_customer_features',
        input_tables=['analytics.reporting.customer_summary'],
        output_table='ml.features.customer_features',
        query_text="""
            SELECT
                customer_id,
                CASE WHEN total_orders < 2 THEN 0.8 ELSE 0.2 END as churn_risk,
                total_revenue as lifetime_value,
                CASE
                    WHEN total_revenue > 1000 THEN 'VIP'
                    WHEN total_revenue > 500 THEN 'Regular'
                    ELSE 'New'
                END as segment
            FROM analytics.reporting.customer_summary
        """,
        column_mapping={
            'churn_risk': ['customer_summary.total_orders'],
            'lifetime_value': ['customer_summary.total_revenue'],
            'segment': ['customer_summary.total_revenue']
        }
    )
    print("  [OK] Tracked lineage: customer_features <- customer_summary")

    # Register schema versions
    print()
    print("[STEP 4] Registering Schema Versions")
    print("-" * 80)

    # Register schema for customers table
    schema_registry.register_schema(
        schema_name='production.public.customers',
        columns=[
            {'name': 'customer_id', 'type': 'int', 'nullable': False},
            {'name': 'email', 'type': 'string', 'nullable': False},
            {'name': 'first_name', 'type': 'string', 'nullable': True},
            {'name': 'last_name', 'type': 'string', 'nullable': True},
            {'name': 'created_at', 'type': 'timestamp', 'nullable': True}
        ],
        description='Customer table schema'
    )
    print("  [OK] Registered schema for customers table")

    # Print summary
    print()
    print("=" * 80)
    print("CATALOG POPULATION COMPLETE!".center(80))
    print("=" * 80)
    print()

    # Get statistics
    stats = catalog.get_statistics()
    print("Catalog Statistics:")
    print(f"  Total Assets: {stats['total_assets']}")
    print(f"  Tables: {stats['by_type'].get('table', 0)}")
    print(f"  Columns: {stats['by_type'].get('column', 0)}")
    print(f"  Total Tags: {stats['total_tags']}")
    print()

    print("Lineage Statistics:")
    upstream = lineage.get_upstream_lineage('analytics.reporting.customer_summary', depth=5)
    print(f"  customer_summary has {len(upstream.get('inputs', []))} upstream dependencies")
    print()

    print("Schema Registry:")
    print(f"  Schema registered for customers table")
    print()

    print("Files Created:")
    print(f"  {catalog_path}/catalog.json")
    print(f"  {lineage_path}/lineage.json")
    print(f"  {schema_path}/schemas.json")
    print()

    print("[SUCCESS] NeuroLake catalog populated successfully!")
    print()
    print("Next Steps:")
    print("  1. Restart dashboard: docker-compose restart dashboard")
    print("  2. Open dashboard: http://localhost:5000")
    print("  3. Navigate to Data Catalog tab")
    print("  4. You should see 5 tables with full lineage and schema history")
    print()
    print("=" * 80)

    return catalog_path

if __name__ == "__main__":
    try:
        catalog_path = populate_neurolake_catalog()
        print(f"\nCatalog populated at: {catalog_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
