"""
Populate Dashboard Catalog with Real Data

This script creates real data in the catalog directories that the dashboard uses,
so the data will be visible in the UI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neurolake.catalog import DataCatalog, LineageTracker, SchemaRegistry, AutonomousTransformationTracker, TransformationType
from datetime import datetime

def populate_catalog():
    """Populate the dashboard catalog with real sample data"""

    print("="*80)
    print("POPULATING DASHBOARD CATALOG WITH REAL DATA")
    print("="*80)

    # Initialize catalog with dashboard paths
    print("\n[1/5] Initializing Data Catalog...")
    catalog = DataCatalog(storage_path="./catalog_data")

    print("[2/5] Initializing Lineage Tracker...")
    lineage = LineageTracker(storage_path="./lineage_data")

    print("[3/5] Initializing Schema Registry...")
    schema_registry = SchemaRegistry(storage_path="./schema_registry")

    print("[4/5] Initializing Transformation Tracker...")
    trans_tracker = AutonomousTransformationTracker(storage_path="./transformations")

    print("[5/5] All catalog components initialized!\n")

    # Register sample tables
    print("="*80)
    print("REGISTERING SAMPLE TABLES")
    print("="*80)

    # Table 1: Customers
    print("\n[TABLE 1] Registering 'customers' table...")
    customers_id = catalog.register_table(
        table_name='customers',
        database='production',
        schema='public',
        columns=[
            {'name': 'customer_id', 'type': 'int', 'nullable': False, 'description': 'Unique customer ID'},
            {'name': 'first_name', 'type': 'string', 'nullable': False, 'description': 'Customer first name'},
            {'name': 'last_name', 'type': 'string', 'nullable': False, 'description': 'Customer last name'},
            {'name': 'email', 'type': 'string', 'nullable': False, 'description': 'Customer email address'},
            {'name': 'phone', 'type': 'string', 'nullable': True, 'description': 'Customer phone number'},
            {'name': 'address', 'type': 'string', 'nullable': True, 'description': 'Customer mailing address'},
            {'name': 'city', 'type': 'string', 'nullable': True},
            {'name': 'state', 'type': 'string', 'nullable': True},
            {'name': 'zip_code', 'type': 'string', 'nullable': True},
            {'name': 'country', 'type': 'string', 'nullable': True},
            {'name': 'created_at', 'type': 'timestamp', 'nullable': False},
            {'name': 'updated_at', 'type': 'timestamp', 'nullable': False}
        ],
        description='Customer master data - contains all customer information',
        owner='data_team',
        tags=['production', 'customers', 'core', 'pii'],
        metadata={
            'row_count': 150000,
            'table_size_mb': 45.2,
            'last_updated': datetime.now().isoformat(),
            'data_quality_score': 0.95
        }
    )
    print(f"   ✓ Registered: {customers_id}")
    print(f"   ✓ Columns: 12")
    print(f"   ✓ Tags: production, customers, core, pii")

    # Table 2: Orders
    print("\n[TABLE 2] Registering 'orders' table...")
    orders_id = catalog.register_table(
        table_name='orders',
        database='production',
        schema='public',
        columns=[
            {'name': 'order_id', 'type': 'int', 'nullable': False, 'description': 'Unique order ID'},
            {'name': 'customer_id', 'type': 'int', 'nullable': False, 'description': 'Reference to customer'},
            {'name': 'order_date', 'type': 'timestamp', 'nullable': False, 'description': 'When order was placed'},
            {'name': 'order_status', 'type': 'string', 'nullable': False, 'description': 'pending/shipped/delivered/cancelled'},
            {'name': 'total_amount', 'type': 'decimal', 'nullable': False, 'description': 'Total order value'},
            {'name': 'payment_method', 'type': 'string', 'nullable': True},
            {'name': 'shipping_address', 'type': 'string', 'nullable': True},
            {'name': 'tracking_number', 'type': 'string', 'nullable': True}
        ],
        description='Order transactions - all customer orders',
        owner='data_team',
        tags=['production', 'orders', 'transactional', 'core'],
        metadata={
            'row_count': 580000,
            'table_size_mb': 125.8,
            'last_updated': datetime.now().isoformat()
        }
    )
    print(f"   ✓ Registered: {orders_id}")
    print(f"   ✓ Columns: 8")
    print(f"   ✓ Tags: production, orders, transactional, core")

    # Table 3: Products
    print("\n[TABLE 3] Registering 'products' table...")
    products_id = catalog.register_table(
        table_name='products',
        database='production',
        schema='public',
        columns=[
            {'name': 'product_id', 'type': 'int', 'nullable': False},
            {'name': 'product_name', 'type': 'string', 'nullable': False},
            {'name': 'category', 'type': 'string', 'nullable': False},
            {'name': 'price', 'type': 'decimal', 'nullable': False},
            {'name': 'cost', 'type': 'decimal', 'nullable': False},
            {'name': 'supplier', 'type': 'string', 'nullable': True},
            {'name': 'stock_quantity', 'type': 'int', 'nullable': False}
        ],
        description='Product catalog - all available products',
        owner='product_team',
        tags=['production', 'products', 'catalog', 'inventory'],
        metadata={
            'row_count': 5000,
            'table_size_mb': 2.1
        }
    )
    print(f"   ✓ Registered: {products_id}")

    # Table 4: Analytics - Customer Summary
    print("\n[TABLE 4] Registering 'customer_summary' table...")
    customer_summary_id = catalog.register_table(
        table_name='customer_summary',
        database='analytics',
        schema='reporting',
        columns=[
            {'name': 'customer_id', 'type': 'int', 'nullable': False},
            {'name': 'customer_name', 'type': 'string', 'nullable': False},
            {'name': 'total_orders', 'type': 'int', 'nullable': False},
            {'name': 'total_revenue', 'type': 'decimal', 'nullable': False},
            {'name': 'avg_order_value', 'type': 'decimal', 'nullable': False},
            {'name': 'customer_lifetime_value', 'type': 'decimal', 'nullable': False},
            {'name': 'first_order_date', 'type': 'date', 'nullable': False},
            {'name': 'last_order_date', 'type': 'date', 'nullable': False}
        ],
        description='Customer analytics summary - aggregated customer metrics',
        owner='analytics_team',
        tags=['analytics', 'aggregated', 'reporting', 'kpi'],
        metadata={
            'row_count': 150000,
            'refresh_schedule': 'daily',
            'last_refreshed': datetime.now().isoformat()
        }
    )
    print(f"   ✓ Registered: {customer_summary_id}")

    # Table 5: ML Features
    print("\n[TABLE 5] Registering 'customer_features' table...")
    ml_features_id = catalog.register_table(
        table_name='customer_features',
        database='ml',
        schema='features',
        columns=[
            {'name': 'customer_id', 'type': 'int'},
            {'name': 'recency_days', 'type': 'int'},
            {'name': 'frequency_count', 'type': 'int'},
            {'name': 'monetary_total', 'type': 'decimal'},
            {'name': 'churn_risk_score', 'type': 'float'},
            {'name': 'lifetime_value_prediction', 'type': 'decimal'}
        ],
        description='ML feature store for customer predictions',
        owner='ml_team',
        tags=['ml', 'features', 'predictions', 'rfm'],
        metadata={
            'row_count': 150000,
            'feature_version': '1.2.0'
        }
    )
    print(f"   ✓ Registered: {ml_features_id}")

    # Register lineage
    print("\n" + "="*80)
    print("REGISTERING DATA LINEAGE")
    print("="*80)

    print("\n[LINEAGE 1] customers + orders → customer_summary")
    lineage.track_query_lineage(
        query_id='create_customer_summary',
        input_tables=['production.public.customers', 'production.public.orders'],
        output_table='analytics.reporting.customer_summary',
        query_text="""
            SELECT
                c.customer_id,
                c.first_name || ' ' || c.last_name as customer_name,
                COUNT(o.order_id) as total_orders,
                SUM(o.total_amount) as total_revenue,
                AVG(o.total_amount) as avg_order_value,
                SUM(o.total_amount) as customer_lifetime_value,
                MIN(o.order_date) as first_order_date,
                MAX(o.order_date) as last_order_date
            FROM production.public.customers c
            JOIN production.public.orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id, c.first_name, c.last_name
        """,
        column_mapping={
            'customer_name': ['customers.first_name', 'customers.last_name'],
            'total_orders': ['orders.order_id'],
            'total_revenue': ['orders.total_amount'],
            'customer_lifetime_value': ['orders.total_amount']
        }
    )
    print("   ✓ Query lineage tracked")

    print("\n[LINEAGE 2] customer_summary → customer_features")
    lineage.track_query_lineage(
        query_id='create_customer_features',
        input_tables=['analytics.reporting.customer_summary'],
        output_table='ml.features.customer_features',
        column_mapping={
            'recency_days': ['customer_summary.last_order_date'],
            'frequency_count': ['customer_summary.total_orders'],
            'monetary_total': ['customer_summary.total_revenue']
        }
    )
    print("   ✓ ML feature lineage tracked")

    # Register schemas
    print("\n" + "="*80)
    print("REGISTERING SCHEMAS")
    print("="*80)

    print("\n[SCHEMA 1] Registering customer_schema v1")
    schema_registry.register_schema(
        schema_name='customer_schema',
        columns=[
            {'name': 'customer_id', 'type': 'int', 'nullable': False},
            {'name': 'first_name', 'type': 'string', 'nullable': False},
            {'name': 'last_name', 'type': 'string', 'nullable': False},
            {'name': 'email', 'type': 'string', 'nullable': False}
        ],
        description='Customer schema v1 - initial version'
    )
    print("   ✓ Schema v1 registered")

    print("\n[SCHEMA 2] Registering customer_schema v2 (added phone)")
    schema_registry.register_schema(
        schema_name='customer_schema',
        columns=[
            {'name': 'customer_id', 'type': 'int', 'nullable': False},
            {'name': 'first_name', 'type': 'string', 'nullable': False},
            {'name': 'last_name', 'type': 'string', 'nullable': False},
            {'name': 'email', 'type': 'string', 'nullable': False},
            {'name': 'phone', 'type': 'string', 'nullable': True}
        ],
        description='Customer schema v2 - added phone field'
    )
    print("   ✓ Schema v2 registered (backward compatible)")

    # Register transformations
    print("\n" + "="*80)
    print("REGISTERING TRANSFORMATIONS")
    print("="*80)

    print("\n[TRANSFORM 1] Create full_name from first_name + last_name")
    trans_tracker.capture_transformation(
        transformation_name='Create Full Name',
        transformation_type=TransformationType.COLUMN_DERIVATION,
        input_columns=['first_name', 'last_name'],
        output_columns=['full_name'],
        logic='full_name = first_name + " " + last_name',
        code='df["full_name"] = df["first_name"] + " " + df["last_name"]',
        language='python',
        metadata={'usage_count': 45}
    )
    print("   ✓ Transformation registered")

    print("\n[TRANSFORM 2] Calculate RFM metrics")
    trans_tracker.capture_transformation(
        transformation_name='Calculate RFM Metrics',
        transformation_type=TransformationType.AGGREGATION,
        input_columns=['order_date', 'order_id', 'total_amount'],
        output_columns=['recency', 'frequency', 'monetary'],
        logic='RFM analysis for customer segmentation',
        code='''
            recency = (current_date - MAX(order_date)).days
            frequency = COUNT(order_id)
            monetary = SUM(total_amount)
        ''',
        language='python'
    )
    print("   ✓ Transformation registered")

    # Final statistics
    print("\n" + "="*80)
    print("FINAL STATISTICS")
    print("="*80)

    stats = catalog.get_statistics()
    print(f"\n✓ Total Assets: {stats['total_assets']}")
    print(f"✓ Tables: {stats['by_type'].get('table', 0)}")
    print(f"✓ Columns: {stats['by_type'].get('column', 0)}")
    print(f"✓ Tags: {stats['total_tags']}")

    print("\n" + "="*80)
    print("SUCCESS! Dashboard catalog populated with real data")
    print("="*80)
    print("\nYou can now:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. Click 'Data Catalog' in the sidebar")
    print("3. See all 5 tables in the 'All Assets' tab")
    print("4. Explore lineage in the 'Lineage' tab")
    print("5. View transformations in the 'Transformations' tab")
    print("6. Check schemas in the 'Schemas' tab")
    print("="*80)

    return True

if __name__ == "__main__":
    try:
        populate_catalog()
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
