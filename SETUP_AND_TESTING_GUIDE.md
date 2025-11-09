# NeuroLake Setup and Testing Guide

## Quick Start - Testing Phase 1 Fixes

This guide walks through setting up and testing all the critical integration fixes completed in Phase 1.

---

## Prerequisites

Before starting, ensure you have:
- **Docker & Docker Compose** installed
- **Python 3.11+** installed
- **Node.js 18+** and npm installed
- **PostgreSQL 15+** accessible (via Docker or local)
- **Git** installed

---

## Step 1: Environment Setup

### 1.1 Set up Python Environment

```bash
cd /home/user/neurolake

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov alembic
```

### 1.2 Set up Frontend Environment

```bash
cd frontend

# Install dependencies
npm install

# Install missing dependency (date-fns for DashboardPage)
npm install date-fns

# Copy environment file
cp .env.example .env.local

# Update .env.local with your API URL
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 1.3 Configure Environment Variables

Create `.env` file in project root:

```bash
cp .env.example .env
```

Update `.env` with your values:

```env
# Database
DATABASE_URL=postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO/S3
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=neurolake
S3_SECRET_KEY=dev_password_change_in_prod

# LLM API Keys (optional for testing)
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Application
ENV=development
LOG_LEVEL=debug
```

---

## Step 2: Start Infrastructure Services

### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d postgres redis minio qdrant

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f postgres
```

### Option B: Using Local Services

If running services locally, ensure:
- PostgreSQL is running on port 5432
- Redis is running on port 6379
- MinIO (optional) is running on port 9000

---

## Step 3: Run Database Migrations

### 3.1 Initialize Alembic (if not already done)

```bash
# Check current migration status
alembic current

# Should show: c32f1f4d9189 (initial_schema...)
```

### 3.2 Run New RBAC Migration

```bash
# Apply the RBAC migration
alembic upgrade head

# Verify migration applied
alembic current

# Should show: d4e8b9f2a5c1 (add_rbac_tables)
```

### 3.3 Verify Tables Created

```bash
# Connect to database
psql postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake

# List tables
\dt

# Should see:
# - users (with new columns: is_superuser, is_verified)
# - roles
# - permissions
# - user_roles
# - role_permissions
# - query_history
# - pipelines
# - audit_logs
# - tables
# - columns

# Check roles were seeded
SELECT name, is_system FROM roles ORDER BY name;

# Should see 4 roles: admin, data_analyst, data_engineer, data_viewer

# Check permissions
SELECT COUNT(*) FROM permissions;

# Should see ~20 permissions

# Exit psql
\q
```

---

## Step 4: Run Integration Tests

### 4.1 Run Phase 1 Integration Test Suite

```bash
# From project root
python tests/test_phase1_integration.py
```

Expected output:
```
================================================================================
PHASE 1 INTEGRATION TESTS
================================================================================

✅ Database connection successful
✅ Users table has all required fields
✅ All RBAC tables exist
✅ Default roles seeded correctly
✅ Default permissions seeded correctly
✅ Role permissions assigned correctly
✅ Query history table schema correct
✅ Pipelines table exists with correct schema
✅ Test admin user created successfully
✅ Password hashing works correctly
✅ Database indexes created correctly
✅ Foreign key constraints in place
✅ NeuroLake Engine initialized (backend: duckdb)
✅ Auth service initialized successfully
✅ Compliance engine initialized successfully
✅ Data catalog initialized successfully

================================================================================
RESULTS: 16 passed, 0 failed out of 16 tests
================================================================================

🎉 ALL TESTS PASSED! Phase 1 integration is successful.
```

### 4.2 Run Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=neurolake --cov-report=html
```

---

## Step 5: Test Backend API

### 5.1 Start the API Server

```bash
# From project root with venv activated
python -m uvicorn neurolake.api.main:app --reload --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

### 5.2 Test API Endpoints

Open another terminal and test with curl:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"..."}

# Test API root
curl http://localhost:8000/

# Expected: JSON with API information

# Test OpenAPI docs
# Open in browser: http://localhost:8000/docs
```

### 5.3 Test Authentication

```bash
# Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'

# Expected: User object with id, username, email, etc.

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'

# Expected: {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer",
#   "expires_in": 1800,
#   "user": {...}
# }

# Save the access_token for next requests
export TOKEN="<access_token from above>"
```

### 5.4 Test Query Execution

```bash
# Execute a simple query (requires authentication)
curl -X POST http://localhost:8000/api/v1/queries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT 1 as test_column",
    "limit": 100,
    "optimize": true,
    "check_compliance": true
  }'

# Expected: {
#   "success": true,
#   "query_id": "...",
#   "data": [{"test_column": 1}],
#   "columns": ["test_column"],
#   "row_count": 1,
#   "execution_time_ms": <time>,
#   "optimized": false,
#   "compliance_checked": true,
#   "compliance_warnings": []
# }
```

### 5.5 Test Query History

```bash
# Get query history
curl -X GET "http://localhost:8000/api/v1/queries/history?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Expected: {
#   "queries": [...],
#   "total": <count>,
#   "limit": 10,
#   "offset": 0
# }

# Verify query was saved to database
psql postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake \
  -c "SELECT query_id, query_text, query_status, execution_time_ms FROM query_history ORDER BY created_at DESC LIMIT 5;"
```

### 5.6 Test Pipelines API

```bash
# Create a pipeline
curl -X POST http://localhost:8000/api/v1/pipelines \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "test_pipeline",
    "pipeline_type": "ETL",
    "description": "Test pipeline",
    "source_config": {"type": "csv", "path": "/data/input.csv"},
    "destination_config": {"type": "table", "name": "output_table"}
  }'

# List pipelines
curl -X GET http://localhost:8000/api/v1/pipelines \
  -H "Authorization: Bearer $TOKEN"

# Get pipeline by ID
curl -X GET http://localhost:8000/api/v1/pipelines/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 6: Test Frontend

### 6.1 Start Frontend Development Server

```bash
cd frontend

# Start Next.js dev server
npm run dev

# Server starts on http://localhost:3000
```

### 6.2 Test Frontend Pages

1. **Open browser**: http://localhost:3000

2. **Test Login Page**:
   - Should see login form
   - Enter username: `testuser` (created above)
   - Enter password: `TestPass123!`
   - Click "Sign In"
   - Should redirect to dashboard on success

3. **Test Dashboard**:
   - Should show query statistics
   - Should show recent queries (if any executed)
   - Data should be fetched from backend API

4. **Test Query Page** (optional, needs more work):
   - Navigate to /query
   - Should show query editor placeholder

### 6.3 Verify Frontend-Backend Communication

Open browser DevTools (F12) → Network tab:
- Should see API calls to `http://localhost:8000`
- Should see Authorization header with JWT token
- Should see responses with data

---

## Step 7: Run Full Stack Tests

### 7.1 Start All Services

```bash
# Terminal 1: Start infrastructure
docker-compose up -d

# Terminal 2: Start backend API
python -m uvicorn neurolake.api.main:app --reload

# Terminal 3: Start frontend
cd frontend && npm run dev
```

### 7.2 Run End-to-End Test Scenarios

**Scenario 1: User Registration → Login → Query Execution**

1. Open http://localhost:3000
2. Register new user (if needed)
3. Login with credentials
4. Use curl or API docs to execute a query
5. Refresh dashboard - should see query in history

**Scenario 2: Pipeline Creation → View**

1. Use curl to create a pipeline (see Step 5.6)
2. Verify pipeline appears in database
3. (Future) View pipeline in frontend when UI is built

**Scenario 3: RBAC Verification**

1. Login as different users with different roles
2. Verify permissions are checked
3. Try to access admin endpoint without admin role (should fail)

---

## Step 8: Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection manually
psql postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake -c "SELECT 1"
```

### Migration Issues

```bash
# Check migration status
alembic current

# Downgrade if needed
alembic downgrade -1

# Re-upgrade
alembic upgrade head

# Check for migration errors
alembic history --verbose
```

### API Issues

```bash
# Check API logs
# The terminal running uvicorn will show errors

# Test with verbose curl
curl -v http://localhost:8000/health

# Check environment variables are loaded
python -c "from neurolake.config import get_settings; print(get_settings().database.connection_string)"
```

### Frontend Issues

```bash
# Check Node.js version
node --version  # Should be 18+

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check environment variables
cat frontend/.env.local

# Check browser console for errors (F12)
```

---

## Common Test Scenarios

### Test 1: Complete Authentication Flow

```bash
# 1. Register user
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"flowtest","email":"flow@test.com","password":"Test123!"}')

echo $USER_RESPONSE

# 2. Login
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"flowtest","password":"Test123!"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"

# 3. Execute query
curl -X POST http://localhost:8000/api/v1/queries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT NOW() as current_time"}'

# 4. Check query history
curl -X GET http://localhost:8000/api/v1/queries/history \
  -H "Authorization: Bearer $TOKEN"
```

### Test 2: RBAC Permission Checks

```bash
# Try to access admin endpoint without permissions (should fail)
curl -X GET http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer $TOKEN"

# Expected: 403 Forbidden (unless user is admin)
```

### Test 3: Query History Persistence

```python
# Run in Python REPL
from neurolake.engine import NeuroLakeEngine
from neurolake.db import get_db_session
from sqlalchemy import text

# Execute query
db = get_db_session()
engine = NeuroLakeEngine(db_session=db, user_id=1)
result = engine.execute_sql("SELECT 1 as test")

# Check database
result = db.execute(text("SELECT COUNT(*) FROM query_history"))
count = result.scalar()
print(f"Query history count: {count}")
```

---

## Success Criteria Checklist

After following this guide, verify:

- [ ] All database migrations applied successfully
- [ ] All tables created with correct schema
- [ ] Default roles and permissions seeded
- [ ] Test admin user created
- [ ] Backend API starts without errors
- [ ] Frontend builds and runs
- [ ] Login flow works end-to-end
- [ ] Query execution works
- [ ] Query history persists to database
- [ ] Dashboard shows real data
- [ ] Pipelines API functional
- [ ] All Phase 1 integration tests pass

---

## Next Steps

Once all tests pass:

1. **Phase 2**: Create remaining API routers (agents, audit, compliance)
2. **Phase 3**: Write comprehensive integration tests
3. **Phase 4**: Integrate catalog with ingestion
4. **Phase 5**: Add monitoring and tracing
5. **Phase 6**: Production deployment preparation

---

## Getting Help

If you encounter issues:

1. Check this guide's Troubleshooting section
2. Review `IMPLEMENTATION_PROGRESS.md` for known issues
3. Check application logs for errors
4. Verify all environment variables are set correctly
5. Ensure all services are running

---

**Document Version**: 1.0
**Last Updated**: 2025-11-09
**Status**: Phase 1 Testing Ready
