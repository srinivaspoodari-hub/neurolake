# NeuroLake Platform - Code Structure Guide

**Quick Reference for Developers**

---

## Directory Structure

```
neurolake/
│
├── 📱 Frontend UIs
│   ├── advanced_databricks_dashboard.py    Main dashboard (7,500 lines)
│   ├── neurolake_ui_integration.html       NDM + NUIC UI (44 KB)
│   ├── migration_ui.html                   Migration UI
│   └── notebook_ui.html                    Notebook UI
│
├── 🔌 API Integration
│   ├── neurolake_api_integration.py        NDM + NUIC API (25 endpoints)
│   ├── notebook_api_endpoints.py           Notebook API
│   └── [Other API modules]
│
├── 🧠 Core Platform (neurolake/)
│   │
│   ├── 📊 Query Engine (engine/)
│   │   ├── __init__.py
│   │   ├── neurolake_engine.py             Main query engine
│   │   ├── query_planner.py                Plan generation
│   │   ├── executor.py                     Query execution
│   │   └── templates.py                    Query templates
│   │
│   ├── 🤖 LLM Integration (llm/)
│   │   ├── __init__.py
│   │   ├── llm_factory.py                  Multi-LLM support
│   │   ├── config.py                       Configuration
│   │   └── usage_tracker.py                Token tracking
│   │
│   ├── 🎯 AI Agents (agents/)
│   │   ├── __init__.py
│   │   ├── base_agent.py                   Base agent class
│   │   ├── data_engineer_agent.py          Data engineer agent
│   │   ├── coordinator.py                  Multi-agent orchestration
│   │   └── tools.py                        Agent tools
│   │
│   ├── 💬 Intent Parsing (intent/)
│   │   ├── __init__.py
│   │   ├── intent_parser.py                NL → SQL conversion
│   │   └── patterns.py                     Intent patterns
│   │
│   ├── 🔒 Compliance (compliance/)
│   │   ├── __init__.py
│   │   ├── compliance_engine.py            Policy enforcement
│   │   ├── pii_detector.py                 PII detection
│   │   ├── audit_logger.py                 Audit logging
│   │   └── policies.py                     Policy definitions
│   │
│   ├── ⚡ Optimization (optimizer/)
│   │   ├── __init__.py
│   │   ├── query_optimizer.py              Cost/performance optimizer
│   │   ├── rules.py                        Optimization rules
│   │   └── stats.py                        Statistics collector
│   │
│   ├── 💾 Caching (cache/)
│   │   ├── __init__.py
│   │   ├── cache_manager.py                Cache operations
│   │   └── strategies.py                   Caching strategies
│   │
│   ├── 📥 Data Ingestion - NDM (ingestion/)
│   │   ├── __init__.py
│   │   ├── smart_ingestion.py              Smart ingestor (622 lines)
│   │   └── file_handler.py                 File processing
│   │
│   ├── 📚 Unified Catalog - NUIC (nuic/)
│   │   ├── __init__.py
│   │   ├── catalog_engine.py               Catalog management (709 lines)
│   │   ├── catalog_api.py                  Catalog query API
│   │   ├── lineage_graph.py                Lineage tracking (693 lines)
│   │   ├── schema_evolution.py             Schema versioning
│   │   ├── pattern_library.py              Reusable patterns
│   │   ├── pipeline_registry.py            Pipeline registry
│   │   └── template_manager.py             Template management
│   │
│   ├── 📋 Data Catalog (catalog/)
│   │   ├── __init__.py
│   │   ├── data_catalog.py                 Catalog operations
│   │   ├── metadata_store.py               Metadata storage
│   │   ├── lineage_tracker.py              Lineage tracking
│   │   ├── schema_registry.py              Schema registry
│   │   └── autonomous_transformation.py    Auto transforms
│   │
│   ├── 📊 Dashboard Components (dashboard/)
│   │   ├── __init__.py
│   │   └── README.md
│   │
│   ├── 🧠 NeuroBrain (neurobrain/)
│   │   ├── __init__.py
│   │   └── [Brain components]
│   │
│   └── 🔄 Hybrid Layer (hybrid/)
│       ├── __init__.py
│       └── [Hybrid components]
│
├── 🧪 Testing
│   ├── test_ndm_nuic_integration.py        Integration tests (6 tests)
│   ├── test_complete_ndm_flow.py           NDM E2E tests
│   ├── test_complete_platform_integration.py  Platform tests
│   ├── test_notebook_complete_system.py    Notebook tests
│   ├── test_nuic_hybrid.py                 NUIC/Hybrid tests
│   └── neurolake/tests/                    Unit tests
│
├── 📁 Data Storage
│   ├── catalog_data/                       NUIC catalog database
│   ├── data/                               Ingested datasets
│   │   ├── bronze/                         Raw data (quality < 0.5)
│   │   ├── silver/                         Cleaned data (0.5-0.8)
│   │   └── gold/                           Curated data (>= 0.8)
│   ├── test_data_ndm/                      NDM test data
│   ├── test_lineage_data/                  Lineage test data
│   └── test_schema_registry/               Schema test data
│
├── 🐳 Infrastructure
│   ├── docker-compose.yml                  Main compose file
│   ├── docker-compose.migration.yml        Migration compose
│   ├── Dockerfile.dashboard                Dashboard container
│   ├── frontend/Dockerfile                 Frontend container
│   │
│   ├── k8s/                                Kubernetes manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress/
│   │   ├── cert-manager/
│   │   ├── autoscaling/
│   │   ├── monitoring/
│   │   └── logging/
│   │
│   └── helm/                               Helm charts
│       └── neurolake/
│
├── 🚀 Launch Scripts
│   ├── start_dashboard.bat                 Windows launcher
│   ├── start-migration.bat                 Migration launcher (Windows)
│   └── start-migration.sh                  Migration launcher (Linux/Mac)
│
├── 📖 Documentation
│   ├── README.md                           Project overview
│   ├── START_HERE.md                       Quick start guide
│   ├── ARCHITECTURE_DIAGRAMS.md            Complete architecture (this doc)
│   ├── FLOW_DIAGRAMS.md                    Mermaid flow diagrams
│   ├── CODE_STRUCTURE_GUIDE.md             This file
│   ├── NDM_NUIC_INTEGRATION_COMPLETE.md    Integration docs
│   ├── VERIFICATION_CHECKLIST.md           Verification checklist
│   ├── FEATURES_GAP_ANALYSIS.md            Gap analysis
│   ├── ARCHITECTURE.md                     Technical architecture
│   ├── COMPETITIVE_ANALYSIS.md             Market analysis
│   ├── BUSINESS_PLAN.md                    Business strategy
│   ├── NEXT_STEPS.md                       Implementation plan
│   ├── HOW_IT_WORKS.md                     How it works
│   ├── DOCKER_QUICKSTART.md                Docker guide
│   └── [Other docs]
│
├── 📦 Dependencies
│   ├── requirements.txt                    Python dependencies
│   └── requirements-dev.txt                Dev dependencies
│
└── ⚙️ Configuration
    ├── .env                                Environment variables
    ├── .gitignore                          Git ignore rules
    └── pyproject.toml                      Python project config
```

---

## Key Files by Function

### 🎯 Want to modify the main dashboard?
**File**: `advanced_databricks_dashboard.py` (7,500 lines)
- Contains all UI routes
- API gateway
- WebSocket handlers
- Integrates all routers

### 📥 Want to modify file upload/ingestion?
**Files**:
- `neurolake/ingestion/smart_ingestion.py` - Main ingestion logic
- `neurolake/ingestion/file_handler.py` - File parsing
- `neurolake_api_integration.py` - API endpoints (lines 76-149)
- `neurolake_ui_integration.html` - UI (lines 1-200)

### 📚 Want to modify catalog/search?
**Files**:
- `neurolake/nuic/catalog_engine.py` - Catalog management
- `neurolake/nuic/catalog_api.py` - Search API
- `neurolake_api_integration.py` - API endpoints (lines 150-275)
- `neurolake_ui_integration.html` - UI (lines 200-400)

### 🔗 Want to modify lineage tracking?
**Files**:
- `neurolake/nuic/lineage_graph.py` - Lineage logic (693 lines)
- `neurolake_api_integration.py` - API endpoints (lines 298-438)
- `neurolake_ui_integration.html` - UI (lines 400-600)

### 📊 Want to modify schema evolution?
**Files**:
- `neurolake/nuic/schema_evolution.py` - Schema tracking
- `neurolake_api_integration.py` - API endpoints (lines 442-508)
- `neurolake_ui_integration.html` - UI (lines 600-800)

### 📈 Want to modify quality metrics?
**Files**:
- `neurolake/ingestion/smart_ingestion.py` - Quality assessment (8 dimensions)
- `neurolake_api_integration.py` - API endpoints (lines 512-559)
- `neurolake_ui_integration.html` - UI (lines 800-1000)

### 🤖 Want to modify AI/LLM integration?
**Files**:
- `neurolake/llm/llm_factory.py` - LLM clients
- `neurolake/agents/data_engineer_agent.py` - AI agent
- `neurolake/intent/intent_parser.py` - NL → SQL
- `advanced_databricks_dashboard.py` - WebSocket handlers

### 🔄 Want to modify migration module?
**Files**:
- `migration_module/` - Complete migration system
- `migration_ui.html` - Migration UI
- `advanced_databricks_dashboard.py` - Migration API

### 📓 Want to modify notebooks?
**Files**:
- `neurolake_notebook_system.py` - Notebook engine
- `notebook_api_endpoints.py` - Notebook API
- `notebook_ui.html` - Notebook UI
- `notebook_advanced_features.py` - Advanced features

---

## Code Organization Principles

### 1. Separation of Concerns
```
Frontend (HTML/JS) → API Gateway (FastAPI) → Business Logic (Python) → Storage (DB/Files)
```

### 2. Module Independence
Each module (`ingestion`, `nuic`, `catalog`, etc.) is self-contained and can be used independently.

### 3. API-First Design
All functionality is exposed via REST APIs, making it easy to add new frontends.

### 4. Configuration-Driven
Most behavior is configurable via environment variables and config files.

### 5. Test Coverage
Every major component has corresponding tests in `neurolake/tests/` or root-level test files.

---

## Data Flow Through Code

### Example: File Upload

```
1. User drops file in UI
   → neurolake_ui_integration.html (line ~150)

2. JavaScript sends HTTP POST
   → fetch('/api/neurolake/ingestion/upload')

3. API Gateway receives request
   → neurolake_api_integration.py:upload_and_ingest() (line 76)

4. Creates SmartIngestor instance
   → from neurolake.ingestion import SmartIngestor (line 16)

5. Calls ingest method
   → smart_ingestion.py:ingest() (line ~100)

6. Performs quality assessment
   → smart_ingestion.py:assess_quality() (line ~300)

7. Routes to appropriate zone
   → smart_ingestion.py:route_data() (line ~400)

8. Writes to storage
   → Saves Parquet file to data/bronze|silver|gold/

9. Registers in catalog
   → Calls NUIC engine to register metadata

10. Tracks lineage
    → Records ingestion event in lineage graph

11. Returns result to API
    → IngestionResult object

12. API formats response
    → Returns JSON with ingestion details

13. UI displays result
    → Shows success message with statistics
```

---

## Key Classes and Their Locations

| Class | File | Purpose |
|-------|------|---------|
| `SmartIngestor` | `neurolake/ingestion/smart_ingestion.py` | Main ingestion orchestrator |
| `NUICEngine` | `neurolake/nuic/catalog_engine.py` | Unified catalog engine |
| `CatalogQueryAPI` | `neurolake/nuic/catalog_api.py` | Catalog search and discovery |
| `LineageGraph` | `neurolake/nuic/lineage_graph.py` | Lineage tracking and visualization |
| `SchemaEvolutionTracker` | `neurolake/nuic/schema_evolution.py` | Schema versioning |
| `NeuroLakeEngine` | `neurolake/engine/neurolake_engine.py` | Query execution engine |
| `LLMFactory` | `neurolake/llm/llm_factory.py` | Multi-LLM client factory |
| `DataEngineerAgent` | `neurolake/agents/data_engineer_agent.py` | AI agent for data tasks |
| `IntentParser` | `neurolake/intent/intent_parser.py` | Natural language parser |
| `ComplianceEngine` | `neurolake/compliance/compliance_engine.py` | Policy enforcement |
| `QueryOptimizer` | `neurolake/optimizer/query_optimizer.py` | Query optimization |
| `CacheManager` | `neurolake/cache/cache_manager.py` | Caching layer |

---

## Configuration Files

### Environment Variables (.env)
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=neurolake
DB_USER=neurolake
DB_PASSWORD=***

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=***
MINIO_SECRET_KEY=***

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM
ANTHROPIC_API_KEY=***
OPENAI_API_KEY=***

# Monitoring
PROMETHEUS_URL=http://localhost:9090
```

### Python Dependencies (requirements.txt)
```
# Data Processing
polars>=1.12.0
pandas>=2.1.0
pyarrow>=18.0.0
duckdb>=1.0.0

# AI/ML
langchain>=0.3.0
anthropic>=0.39.0
openai>=1.50.0
torch>=2.5.0

# API
fastapi>=0.115.0
uvicorn>=0.30.0
pydantic>=2.9.0

# Storage
psycopg2-binary>=2.9.0
redis>=5.1.0

# [See full list in requirements.txt]
```

---

## API Endpoint Map

```
FastAPI App (advanced_databricks_dashboard.py)
│
├── /                          → Main dashboard HTML
├── /ndm-nuic                  → NDM + NUIC UI HTML
├── /migration                 → Migration UI HTML
├── /notebook                  → Notebook UI HTML
├── /docs                      → OpenAPI docs
├── /redoc                     → ReDoc docs
│
├── /api/query/*               → Query execution
│   ├── POST /execute
│   ├── POST /explain
│   ├── POST /validate
│   ├── GET  /history
│   └── GET  /metrics
│
├── /api/neurolake/*           → NDM + NUIC (neurolake_api_integration.py)
│   ├── /ingestion/*           → Data ingestion
│   │   ├── POST /upload
│   │   └── GET  /statistics
│   │
│   ├── /catalog/*             → Catalog operations
│   │   ├── GET /search
│   │   ├── GET /dataset/{id}
│   │   ├── GET /insights/{id}
│   │   ├── GET /popular
│   │   ├── GET /quality-leaders
│   │   └── GET /statistics
│   │
│   ├── /lineage/*             → Lineage tracking
│   │   ├── GET /downstream/{id}
│   │   ├── GET /upstream/{id}
│   │   ├── GET /impact/{id}
│   │   └── GET /full-graph
│   │
│   ├── /schema/*              → Schema evolution
│   │   ├── GET /history/{id}
│   │   └── GET /compare/{id}
│   │
│   ├── /quality/*             → Quality metrics
│   │   ├── GET /time-series/{id}
│   │   └── GET /current/{id}
│   │
│   └── /system/*              → System status
│       ├── GET /status
│       └── GET /health
│
├── /api/notebook/*            → Notebook operations
│   ├── POST   /create
│   ├── GET    /{id}
│   ├── PUT    /{id}
│   ├── DELETE /{id}
│   └── POST   /{id}/execute
│
├── /api/migration/*           → Code migration
│   ├── POST /upload
│   ├── POST /convert
│   └── GET  /status/{id}
│
├── /api/ai/*                  → AI/LLM
│   ├── POST /chat
│   ├── POST /nl-to-sql
│   └── GET  /usage
│
└── /ws/chat                   → WebSocket for AI chat
```

---

## Testing Structure

```
Root Level Tests (Integration & E2E)
├── test_ndm_nuic_integration.py        Verify NDM + NUIC integration
├── test_complete_ndm_flow.py           Test complete ingestion flow
├── test_complete_platform_integration.py  Full platform test
├── test_notebook_complete_system.py    Notebook system test
└── test_nuic_hybrid.py                 NUIC/Hybrid test

Unit Tests (neurolake/tests/)
├── test_ingestion.py                   Ingestion unit tests
├── test_catalog.py                     Catalog unit tests
├── test_lineage.py                     Lineage unit tests
├── test_schema_evolution.py            Schema tests
└── [Other unit tests]

How to Run:
# All integration tests
python -m pytest .

# Specific test file
python test_ndm_nuic_integration.py

# Unit tests only
python -m pytest neurolake/tests/

# With coverage
python -m pytest --cov=neurolake
```

---

## Quick Development Tips

### Adding a New API Endpoint

1. **Add endpoint to router**:
   ```python
   # In neurolake_api_integration.py
   @router.get("/my-endpoint/{id}")
   async def my_endpoint(id: str):
       # Your logic here
       return {"result": "success"}
   ```

2. **Endpoint is automatically available**:
   - API: `http://localhost:8000/api/neurolake/my-endpoint/123`
   - Docs: `http://localhost:8000/docs` (auto-generated)

### Adding a New UI Section

1. **Add HTML section**:
   ```html
   <!-- In neurolake_ui_integration.html -->
   <section id="my-section">
       <h2>My Feature</h2>
       <!-- Your UI here -->
   </section>
   ```

2. **Add JavaScript handler**:
   ```javascript
   async function loadMyFeature() {
       const response = await fetch('/api/neurolake/my-endpoint');
       const data = await response.json();
       // Update UI
   }
   ```

### Adding a New Core Module

1. **Create directory**:
   ```bash
   mkdir neurolake/my_module
   ```

2. **Create `__init__.py`**:
   ```python
   from .my_module import MyClass
   __all__ = ['MyClass']
   ```

3. **Import in API**:
   ```python
   from neurolake.my_module import MyClass
   ```

---

## Debugging Guide

### Frontend Issues
- Open browser DevTools (F12)
- Check Console for JavaScript errors
- Check Network tab for failed API calls

### API Issues
- Check terminal output for Python errors
- Use `/docs` endpoint to test API directly
- Enable debug mode: `uvicorn app:app --reload --log-level debug`

### Database Issues
- Check SQLite file: `catalog_data/nuic_catalog.db`
- Use DB Browser for SQLite to inspect
- Check logs for SQL errors

### Storage Issues
- Check data directories: `data/bronze/`, `data/silver/`, `data/gold/`
- Verify file permissions
- Check disk space

---

## Performance Optimization

### Query Performance
- File: `neurolake/optimizer/query_optimizer.py`
- Enable caching: `neurolake/cache/cache_manager.py`
- Use Redis for distributed caching

### Ingestion Performance
- File: `neurolake/ingestion/smart_ingestion.py`
- Use batch processing
- Parallel file uploads (future)

### API Performance
- Enable caching middleware
- Use async endpoints (already done)
- Connection pooling for database

---

## Security Checklist

### Authentication (Future)
- Add JWT middleware in `advanced_databricks_dashboard.py`
- Protect API endpoints
- Use HTTPS in production

### Authorization (Future)
- Implement RBAC
- Row-level security
- Column-level masking

### Compliance
- Already implemented: `neurolake/compliance/compliance_engine.py`
- PII detection: `neurolake/compliance/pii_detector.py`
- Audit logging: `neurolake/compliance/audit_logger.py`

---

**Generated**: November 7, 2025
**Version**: 1.0
**For**: Developer Reference
