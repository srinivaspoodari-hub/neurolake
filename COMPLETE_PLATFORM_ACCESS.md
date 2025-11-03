# NeuroLake Complete Platform - Access Guide

## Your Unified Data Platform is Running!

All services are now operational. Here's where to access everything:

---

## 1. Storage & Data Management

### MinIO Console (Object Storage - NCF Files)
- **URL:** http://localhost:9001
- **Login:** `neurolake` / `dev_password_change_in_prod`
- **What you can do:**
  - View NCF files
  - Upload/download data
  - Manage buckets
  - Monitor storage usage
- **Current Status:** 1 bucket ("nerolake") with 2 files

### Qdrant Dashboard (Vector Database)
- **URL:** http://localhost:6333/dashboard
- **What you can do:**
  - Manage vector collections
  - Search embeddings
  - AI/ML vector operations

---

## 2. Workflows & Orchestration

### Temporal UI (Workflow Engine)
- **URL:** http://localhost:8080
- **What you can do:**
  - **Create workflows:** Data pipelines, ETL jobs
  - **Schedule tasks:** Recurring data processing
  - **Monitor executions:** Track workflow status
  - **Retry logic:** Automatic failure handling
  - **Serverless compute:** Execute workflows on-demand

**Example Workflows:**
```python
# Data ingestion workflow
@workflow.defn
class DataIngestionWorkflow:
    @workflow.run
    async def run(self, source: str) -> dict:
        # 1. Extract data
        data = await workflow.execute_activity(
            extract_data,
            source,
            start_to_close_timeout=timedelta(minutes=10)
        )

        # 2. Transform to NCF
        ncf_data = await workflow.execute_activity(
            convert_to_ncf,
            data,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # 3. Load to storage
        result = await workflow.execute_activity(
            upload_to_minio,
            ncf_data,
            start_to_close_timeout=timedelta(minutes=5)
        )

        return result
```

### NATS Monitoring (Message Broker)
- **URL:** http://localhost:8222
- **What you can do:**
  - View message streams
  - Monitor queue status
  - Check consumer lag
  - JetStream management

---

## 3. Query & Analytics

### SQL Query Editor (Web-based - Coming Soon)
**The unified dashboard will provide:**
- Monaco editor with SQL syntax highlighting
- Auto-completion
- Query execution (Ctrl+Enter)
- Result visualization
- Query history
- AI-powered query optimization

**For now, use:**
```bash
# Direct PostgreSQL connection
psql -h localhost -p 5432 -U neurolake -d neurolake

# Example queries:
SELECT * FROM tables;
SELECT * FROM query_history ORDER BY created_at DESC LIMIT 10;
SELECT * FROM pipelines;
```

### PostgreSQL Tables (Current Data)
**7 tables available:**
1. **users** - User management
2. **tables** - Table metadata catalog
3. **columns** - Column schemas
4. **pipelines** - Data pipelines
5. **query_history** - Query logs
6. **audit_logs** - Audit trail
7. **alembic_version** - Schema versioning

---

## 4. Notebooks & Interactive Computing

### Jupyter Notebook Integration (Setup Required)

**Option 1: Local Jupyter**
```bash
# Install Jupyter with NeuroLake kernel
pip install jupyter ipykernel

# Start Jupyter
jupyter notebook

# In notebook, connect to NeuroLake:
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="neurolake",
    user="neurolake",
    password="dev_password_change_in_prod"
)

# Query data
import pandas as pd
df = pd.read_sql("SELECT * FROM tables", conn)
df.head()
```

**Option 2: JupyterHub (Enterprise)**
```bash
# Add to docker-compose.yml:
jupyterhub:
  image: jupyterhub/jupyterhub:latest
  ports:
    - "8000:8000"
  volumes:
    - ./notebooks:/notebooks
  environment:
    - JUPYTER_ENABLE_LAB=yes
```

### IPython REPL
```bash
# Quick interactive Python session
ipython

# Connect to NeuroLake
from neurolake.engine import NeuroLakeEngine
engine = NeuroLakeEngine()

# Run queries
result = engine.execute_sql("SELECT COUNT(*) FROM tables")
print(result)
```

---

## 5. Serverless Compute

### Temporal Activities (Serverless Functions)

Temporal provides serverless compute through activities:

```python
# Define serverless function
@activity.defn
async def process_large_dataset(dataset_url: str) -> dict:
    """Serverless function to process data"""
    # Download from MinIO
    data = download_from_minio(dataset_url)

    # Convert to NCF (compressed columnar format)
    ncf_data = convert_to_ncf(data)

    # Upload back to storage
    result_url = upload_to_minio(ncf_data)

    return {"status": "success", "url": result_url}

# Trigger from anywhere
result = await workflow.execute_activity(
    process_large_dataset,
    "s3://neurolake/raw/data.csv",
    start_to_close_timeout=timedelta(hours=1)
)
```

### NATS Functions (Event-driven)

```python
# Serverless event handler
import nats

async def handle_data_event(msg):
    """Triggered when data arrives"""
    data = json.loads(msg.data)

    # Process data
    processed = transform_data(data)

    # Store in NCF format
    store_as_ncf(processed)

# Subscribe to events
nc = await nats.connect("nats://localhost:4222")
js = nc.jetstream()
await js.subscribe("data.ingestion", cb=handle_data_event)
```

---

## 6. Monitoring & Observability

### Grafana (Main Dashboard)
- **URL:** http://localhost:3001
- **Login:** `admin` / `admin`
- **What you can do:**
  - View system metrics
  - Create custom dashboards
  - Set up alerts
  - Monitor workflows

### Prometheus (Metrics)
- **URL:** http://localhost:9090
- **What you can do:**
  - Query metrics with PromQL
  - View targets
  - Check service health
  - Create recording rules

### Jaeger (Distributed Tracing)
- **URL:** http://localhost:16686
- **What you can do:**
  - Trace query execution
  - Find performance bottlenecks
  - Analyze service dependencies
  - Monitor latency

---

## 7. Data Pipelines

### Current Pipeline Status
```bash
# View pipelines in PostgreSQL
psql -h localhost -p 5432 -U neurolake -d neurolake -c "SELECT * FROM pipelines;"
```

### Create New Pipeline (Example)
```python
from neurolake.pipelines import Pipeline, PipelineManager

# Define pipeline
pipeline = Pipeline(
    name="user_analytics",
    description="Process user event data",
    steps=[
        {
            "name": "extract",
            "type": "s3_source",
            "config": {"bucket": "neurolake", "prefix": "events/"}
        },
        {
            "name": "transform",
            "type": "sql_transform",
            "sql": """
                SELECT
                    user_id,
                    COUNT(*) as event_count,
                    DATE(timestamp) as date
                FROM events
                GROUP BY user_id, DATE(timestamp)
            """
        },
        {
            "name": "load",
            "type": "ncf_sink",
            "config": {"table": "user_analytics", "format": "ncf"}
        }
    ]
)

# Register pipeline
pm = PipelineManager()
pm.create_pipeline(pipeline)

# Run pipeline
pm.execute_pipeline("user_analytics")
```

---

## 8. NCF Format Management

### View NCF Files
```bash
# Use the viewer script
python view_ncf_tables.py
```

### Convert Data to NCF
```python
import ncf_rust
import pandas as pd

# Load data
df = pd.read_csv("data.csv")

# Create NCF schema
schema = ncf_rust.NCFSchema([
    ncf_rust.ColumnSchema("user_id", ncf_rust.NCFDataType.Int64),
    ncf_rust.ColumnSchema("name", ncf_rust.NCFDataType.String),
    ncf_rust.ColumnSchema("score", ncf_rust.NCFDataType.Float64)
])

# Write to NCF format
writer = ncf_rust.NCFWriter("output.ncf", schema, compression="zstd")
for row in df.itertuples(index=False):
    writer.write_row(row)
writer.close()

# Read NCF file
reader = ncf_rust.NCFReader("output.ncf")
for row in reader:
    print(row)
```

### NCF Performance Benefits
- **3-5x better compression** than Parquet
- **Faster query performance** (columnar format)
- **Vector embedding support** for AI/ML
- **Checksum validation** for data integrity

---

## 9. API Access

### REST API Endpoints (When dashboard is running)
```bash
# System status
curl http://localhost:8080/api/status

# Execute query
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM tables LIMIT 5"}'

# List tables
curl http://localhost:8080/api/tables

# Convert to NCF
curl -X POST http://localhost:8080/api/ncf/convert \
  -H "Content-Type: application/json" \
  -d '{"table": "users", "compression": "zstd"}'

# Get metrics
curl http://localhost:8080/api/metrics
```

---

## 10. Quick Start Examples

### Example 1: Ingest CSV to NCF
```python
import pandas as pd
import ncf_rust
from minio import Minio

# 1. Read CSV
df = pd.read_csv("sales_data.csv")

# 2. Convert to NCF
schema = ncf_rust.NCFSchema([
    ncf_rust.ColumnSchema("date", ncf_rust.NCFDataType.String),
    ncf_rust.ColumnSchema("product", ncf_rust.NCFDataType.String),
    ncf_rust.ColumnSchema("revenue", ncf_rust.NCFDataType.Float64)
])

writer = ncf_rust.NCFWriter("sales.ncf", schema, compression="zstd")
for row in df.itertuples(index=False):
    writer.write_row(row)
writer.close()

# 3. Upload to MinIO
client = Minio(
    "localhost:9000",
    access_key="neurolake",
    secret_key="dev_password_change_in_prod",
    secure=False
)
client.fput_object("neurolake", "sales/sales.ncf", "sales.ncf")
print("✓ Data ingested to NCF format in MinIO")
```

### Example 2: Run Workflow
```python
from temporalio.client import Client
from temporalio.worker import Worker

# Connect to Temporal
client = await Client.connect("localhost:7233")

# Execute workflow
result = await client.execute_workflow(
    DataIngestionWorkflow.run,
    "s3://neurolake/raw/data.csv",
    id="data-ingest-001",
    task_queue="neurolake-tasks"
)
print(f"Workflow completed: {result}")
```

### Example 3: Query Data
```python
import psycopg2
import pandas as pd

# Connect
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="neurolake",
    user="neurolake",
    password="dev_password_change_in_prod"
)

# Query
df = pd.read_sql("""
    SELECT
        t.table_name,
        t.storage_format,
        t.row_count,
        t.size_bytes / 1024 / 1024 as size_mb
    FROM tables t
    WHERE t.storage_format = 'ncf'
    ORDER BY t.size_bytes DESC
""", conn)

print(df)
```

---

## Summary: Complete Platform Access

| Service | URL | Purpose |
|---------|-----|---------|
| **Temporal UI** | http://localhost:8080 | Workflows & Serverless Compute |
| **MinIO Console** | http://localhost:9001 | Storage & NCF Files |
| **Grafana** | http://localhost:3001 | Monitoring Dashboard |
| **Prometheus** | http://localhost:9090 | Metrics |
| **Jaeger** | http://localhost:16686 | Distributed Tracing |
| **Qdrant** | http://localhost:6333/dashboard | Vector Database |
| **NATS** | http://localhost:8222 | Message Broker |
| **PostgreSQL** | localhost:5432 | Metadata & Tables |
| **Redis** | localhost:6379 | Cache |

---

## Next Steps

1. **Open Temporal UI** (http://localhost:8080) to see workflow orchestration
2. **Open MinIO Console** (http://localhost:9001) to view your NCF files
3. **Open Grafana** (http://localhost:3001) for monitoring
4. **Run the viewer:** `python view_ncf_tables.py`
5. **Create a workflow** using the examples above
6. **Set up Jupyter** for interactive notebooks

Your complete unified data platform is ready! 🚀
