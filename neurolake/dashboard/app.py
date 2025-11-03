"""
NeuroLake Unified Dashboard Application
========================================

A comprehensive web interface integrating all NeuroLake features:
- SQL Query Editor with autocomplete
- Data Explorer and Metadata Browser
- Query History and Performance Analytics
- System Monitoring (metrics, logs, traces)
- NCF Format Management
- AI-powered Query Optimization
- Real-time Data Processing

Similar to Databricks workspace.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import NeuroLake components
from neurolake.engine import NeuroLakeEngine
from neurolake.metadata import MetadataManager
from neurolake.monitoring import MetricsCollector
from neurolake.query_history import QueryHistoryManager

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """SQL query request model"""
    sql: str
    database: Optional[str] = None
    limit: Optional[int] = 1000


class QueryResponse(BaseModel):
    """SQL query response model"""
    success: bool
    data: Optional[list] = None
    columns: Optional[list] = None
    row_count: int = 0
    execution_time_ms: float = 0
    query_id: Optional[str] = None
    error: Optional[str] = None


class TableInfo(BaseModel):
    """Table metadata model"""
    name: str
    database: str
    schema: dict
    row_count: int
    size_bytes: int
    format: str
    partitions: list
    created_at: str
    updated_at: str


class SystemStatus(BaseModel):
    """System status model"""
    status: str
    version: str
    uptime_seconds: float
    active_queries: int
    total_tables: int
    total_queries: int
    storage_used_gb: float
    cpu_percent: float
    memory_percent: float


def create_dashboard_app() -> FastAPI:
    """
    Create the unified NeuroLake dashboard application.

    Returns:
        FastAPI application instance
    """

    app = FastAPI(
        title="NeuroLake Dashboard",
        description="Unified interface for NeuroLake AI-Native Data Platform",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize NeuroLake engine
    engine = NeuroLakeEngine()
    metadata_manager = MetadataManager()
    metrics_collector = MetricsCollector()
    query_history = QueryHistoryManager()

    # Store active WebSocket connections
    active_connections = []


    # ==================== API Endpoints ====================

    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home():
        """Serve the main dashboard UI"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NeuroLake Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs/editor/editor.main.css" rel="stylesheet">
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
                .sidebar {
                    width: 250px;
                    height: 100vh;
                    position: fixed;
                    background: #1e1e1e;
                    color: white;
                    padding-top: 60px;
                }
                .sidebar a {
                    color: #e0e0e0;
                    text-decoration: none;
                    display: block;
                    padding: 12px 20px;
                    transition: background 0.3s;
                }
                .sidebar a:hover, .sidebar a.active { background: #2d2d2d; }
                .main-content { margin-left: 250px; padding: 80px 20px 20px 20px; }
                .navbar { position: fixed; top: 0; left: 250px; right: 0; z-index: 1000; background: white; border-bottom: 1px solid #ddd; }
                .status-badge { font-size: 0.75rem; padding: 2px 8px; }
                #query-editor { height: 400px; border: 1px solid #ddd; }
                .result-table { max-height: 500px; overflow-y: auto; }
                .metric-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .chart-container { height: 300px; margin-top: 20px; }
                .tab-content { padding: 20px; background: white; border: 1px solid #ddd; border-top: none; }
            </style>
        </head>
        <body>
            <!-- Navbar -->
            <nav class="navbar navbar-expand-lg navbar-light bg-white px-4">
                <div class="container-fluid">
                    <h4 class="mb-0"><i class="fas fa-database text-primary"></i> NeuroLake Dashboard</h4>
                    <div class="d-flex align-items-center">
                        <span class="status-badge badge bg-success me-3">
                            <i class="fas fa-circle"></i> Online
                        </span>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                <i class="fas fa-user-circle"></i> Admin
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#"><i class="fas fa-cog"></i> Settings</a></li>
                                <li><a class="dropdown-item" href="#"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </nav>

            <!-- Sidebar -->
            <div class="sidebar">
                <div class="px-3 mb-4">
                    <h5><i class="fas fa-brain text-primary"></i> NeuroLake</h5>
                    <small class="text-muted">AI-Native Data Platform</small>
                </div>
                <a href="#home" class="active" onclick="showTab('home')">
                    <i class="fas fa-home"></i> Home
                </a>
                <a href="#query" onclick="showTab('query')">
                    <i class="fas fa-code"></i> SQL Editor
                </a>
                <a href="#data" onclick="showTab('data')">
                    <i class="fas fa-table"></i> Data Explorer
                </a>
                <a href="#metadata" onclick="showTab('metadata')">
                    <i class="fas fa-info-circle"></i> Metadata
                </a>
                <a href="#history" onclick="showTab('history')">
                    <i class="fas fa-history"></i> Query History
                </a>
                <a href="#ncf" onclick="showTab('ncf')">
                    <i class="fas fa-file-archive"></i> NCF Management
                </a>
                <a href="#monitoring" onclick="showTab('monitoring')">
                    <i class="fas fa-chart-line"></i> Monitoring
                </a>
                <a href="#logs" onclick="showTab('logs')">
                    <i class="fas fa-file-alt"></i> Logs
                </a>
                <a href="#ai" onclick="showTab('ai')">
                    <i class="fas fa-magic"></i> AI Insights
                </a>
                <hr class="border-secondary">
                <a href="#docs" onclick="window.open('/docs', '_blank')">
                    <i class="fas fa-book"></i> API Docs
                </a>
                <a href="#help">
                    <i class="fas fa-question-circle"></i> Help
                </a>
            </div>

            <!-- Main Content -->
            <div class="main-content">
                <!-- Home Tab -->
                <div id="home-tab" class="tab-pane">
                    <h2 class="mb-4">Welcome to NeuroLake</h2>

                    <!-- Metrics Cards -->
                    <div class="row">
                        <div class="col-md-3">
                            <div class="metric-card">
                                <h6>Total Tables</h6>
                                <h2 id="total-tables">-</h2>
                                <small>+12 this week</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                                <h6>Queries Today</h6>
                                <h2 id="queries-today">-</h2>
                                <small>1.2M avg response time</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                                <h6>Storage Used</h6>
                                <h2 id="storage-used">-</h2>
                                <small>45% of capacity</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                                <h6>Active Users</h6>
                                <h2>24</h2>
                                <small>Real-time</small>
                            </div>
                        </div>
                    </div>

                    <!-- Charts -->
                    <div class="row mt-4">
                        <div class="col-md-8">
                            <div class="card">
                                <div class="card-header">
                                    <h5>Query Performance (Last 24h)</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="queryChart" class="chart-container"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card">
                                <div class="card-header">
                                    <h5>Storage by Format</h5>
                                </div>
                                <div class="card-body">
                                    <canvas id="storageChart" class="chart-container"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="row mt-4">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header">
                                    <h5>Recent Activity</h5>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Time</th>
                                                    <th>User</th>
                                                    <th>Action</th>
                                                    <th>Status</th>
                                                    <th>Duration</th>
                                                </tr>
                                            </thead>
                                            <tbody id="activity-table">
                                                <!-- Populated by JavaScript -->
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SQL Editor Tab -->
                <div id="query-tab" class="tab-pane" style="display:none;">
                    <h2 class="mb-4">SQL Query Editor</h2>

                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-3">
                                <div>
                                    <select class="form-select form-select-sm" style="width: 200px;" id="database-select">
                                        <option>default</option>
                                        <option>analytics</option>
                                        <option>staging</option>
                                    </select>
                                </div>
                                <div>
                                    <button class="btn btn-primary btn-sm" onclick="executeQuery()">
                                        <i class="fas fa-play"></i> Run Query (Ctrl+Enter)
                                    </button>
                                    <button class="btn btn-secondary btn-sm" onclick="formatQuery()">
                                        <i class="fas fa-indent"></i> Format
                                    </button>
                                    <button class="btn btn-info btn-sm" onclick="explainQuery()">
                                        <i class="fas fa-info-circle"></i> Explain
                                    </button>
                                    <button class="btn btn-success btn-sm" onclick="optimizeQuery()">
                                        <i class="fas fa-magic"></i> AI Optimize
                                    </button>
                                </div>
                            </div>

                            <div id="query-editor"></div>
                        </div>
                    </div>

                    <!-- Results -->
                    <div class="card">
                        <div class="card-header">
                            <ul class="nav nav-tabs card-header-tabs">
                                <li class="nav-item">
                                    <a class="nav-link active" data-bs-toggle="tab" href="#results-data">Results</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" data-bs-toggle="tab" href="#results-explain">Execution Plan</a>
                                </li>
                                <li class="nav-item">
                                    <a class="nav-link" data-bs-toggle="tab" href="#results-metrics">Metrics</a>
                                </li>
                            </ul>
                        </div>
                        <div class="card-body tab-content">
                            <div class="tab-pane fade show active" id="results-data">
                                <div id="query-status" class="mb-3"></div>
                                <div class="result-table">
                                    <table class="table table-sm table-bordered" id="results-table">
                                        <thead></thead>
                                        <tbody></tbody>
                                    </table>
                                </div>
                            </div>
                            <div class="tab-pane fade" id="results-explain">
                                <pre id="explain-plan"></pre>
                            </div>
                            <div class="tab-pane fade" id="results-metrics">
                                <div id="query-metrics"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Data Explorer Tab -->
                <div id="data-tab" class="tab-pane" style="display:none;">
                    <h2 class="mb-4">Data Explorer</h2>

                    <div class="row">
                        <div class="col-md-3">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Databases & Tables</h6>
                                </div>
                                <div class="card-body">
                                    <div id="table-tree"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-9">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Table Preview</h6>
                                </div>
                                <div class="card-body">
                                    <div id="table-preview"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- NCF Management Tab -->
                <div id="ncf-tab" class="tab-pane" style="display:none;">
                    <h2 class="mb-4">NCF Format Management</h2>

                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        <strong>NeuroLake Columnar Format (NCF)</strong> is optimized for AI/ML workloads with intelligent compression and vector support.
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Convert to NCF</h6>
                                </div>
                                <div class="card-body">
                                    <form onsubmit="convertToNCF(event)">
                                        <div class="mb-3">
                                            <label>Source Table</label>
                                            <input type="text" class="form-control" id="ncf-source-table" placeholder="database.table">
                                        </div>
                                        <div class="mb-3">
                                            <label>Compression</label>
                                            <select class="form-select" id="ncf-compression">
                                                <option value="zstd">ZSTD (Recommended)</option>
                                                <option value="lz4">LZ4 (Fast)</option>
                                                <option value="snappy">Snappy</option>
                                            </select>
                                        </div>
                                        <button type="submit" class="btn btn-primary">
                                            <i class="fas fa-sync"></i> Convert
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6>NCF Statistics</h6>
                                </div>
                                <div class="card-body">
                                    <canvas id="ncfChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Monitoring Tab -->
                <div id="monitoring-tab" class="tab-pane" style="display:none;">
                    <h2 class="mb-4">System Monitoring</h2>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6>CPU Usage</h6>
                                </div>
                                <div class="card-body">
                                    <canvas id="cpuChart"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6>Memory Usage</h6>
                                </div>
                                <div class="card-body">
                                    <canvas id="memoryChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <h6>Active Queries</h6>
                        </div>
                        <div class="card-body">
                            <table class="table" id="active-queries-table">
                                <thead>
                                    <tr>
                                        <th>Query ID</th>
                                        <th>User</th>
                                        <th>Query</th>
                                        <th>Duration</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- AI Insights Tab -->
                <div id="ai-tab" class="tab-pane" style="display:none;">
                    <h2 class="mb-4">AI-Powered Insights</h2>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6>Query Optimization Suggestions</h6>
                                </div>
                                <div class="card-body" id="ai-suggestions">
                                    <p class="text-muted">Run a query to see AI optimization suggestions...</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6>Schema Recommendations</h6>
                                </div>
                                <div class="card-body" id="schema-recommendations">
                                    <p class="text-muted">Analyzing your data patterns...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs/loader.js"></script>
            <script src="/static/dashboard.js"></script>
        </body>
        </html>
        """


    @app.get("/api/status", response_model=SystemStatus)
    async def get_system_status():
        """Get system status and metrics"""
        try:
            metrics = metrics_collector.get_current_metrics()
            return SystemStatus(
                status="healthy",
                version="0.1.0",
                uptime_seconds=metrics.get("uptime", 0),
                active_queries=metrics.get("active_queries", 0),
                total_tables=metadata_manager.get_table_count(),
                total_queries=query_history.get_total_count(),
                storage_used_gb=metrics.get("storage_gb", 0),
                cpu_percent=metrics.get("cpu_percent", 0),
                memory_percent=metrics.get("memory_percent", 0),
            )
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/query", response_model=QueryResponse)
    async def execute_sql_query(request: QueryRequest):
        """Execute SQL query"""
        import time
        start_time = time.time()

        try:
            # Execute query using NeuroLake engine
            result = engine.execute_sql(request.sql, database=request.database)

            # Convert result to list of dicts
            data = result.collect() if hasattr(result, 'collect') else result

            execution_time = (time.time() - start_time) * 1000

            # Save to query history
            query_id = query_history.add_query(
                sql=request.sql,
                database=request.database,
                execution_time_ms=execution_time,
                row_count=len(data) if data else 0,
            )

            return QueryResponse(
                success=True,
                data=data[:request.limit] if data else [],
                columns=list(data[0].keys()) if data else [],
                row_count=len(data) if data else 0,
                execution_time_ms=execution_time,
                query_id=query_id,
            )

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return QueryResponse(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )


    @app.get("/api/tables")
    async def list_tables(database: Optional[str] = None):
        """List all tables"""
        try:
            tables = metadata_manager.list_tables(database=database)
            return {"tables": tables}
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/tables/{database}/{table}", response_model=TableInfo)
    async def get_table_info(database: str, table: str):
        """Get detailed table information"""
        try:
            info = metadata_manager.get_table_info(database, table)
            return TableInfo(**info)
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            raise HTTPException(status_code=404, detail=str(e))


    @app.get("/api/query-history")
    async def get_query_history(limit: int = 100):
        """Get query history"""
        try:
            history = query_history.get_recent(limit=limit)
            return {"queries": history}
        except Exception as e:
            logger.error(f"Error getting query history: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.websocket("/ws/monitoring")
    async def websocket_monitoring(websocket: WebSocket):
        """WebSocket endpoint for real-time monitoring"""
        await websocket.accept()
        active_connections.append(websocket)

        try:
            while True:
                # Send real-time metrics
                metrics = metrics_collector.get_current_metrics()
                await websocket.send_json(metrics)
                await asyncio.sleep(1)

        except WebSocketDisconnect:
            active_connections.remove(websocket)


    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "neurolake-dashboard"}


    # Mount static files if directory exists
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


def run_dashboard(host: str = "0.0.0.0", port: int = 8080, reload: bool = False):
    """
    Run the dashboard application.

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    app = create_dashboard_app()

    logger.info(f"Starting NeuroLake Dashboard on http://{host}:{port}")
    logger.info(f"Access the dashboard at: http://localhost:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_dashboard()
