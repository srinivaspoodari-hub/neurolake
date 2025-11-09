# NeuroLake Docker Deployment Guide

**Date**: January 8, 2025
**Status**: ✅ Ready for Docker Deployment
**Platform**: Windows Docker Desktop

---

## Quick Start (3 Commands)

```bash
# 1. Build and deploy
docker-start-test.bat

# 2. Access dashboard
# Open browser to: http://localhost:5000

# 3. Run E2E tests
python docker-test-e2e.py
```

---

## What's Included in Docker Deployment

### Services Deployed

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **dashboard** | 5000 | NeuroLake unified dashboard | ✅ HTTP /health |
| **postgres** | 5432 | Metadata catalog database | ✅ pg_isready |
| **redis** | 6379 | Caching & session storage | ✅ redis-cli ping |
| **minio** | 9000, 9001 | Object storage (S3-compatible) | ✅ /minio/health/live |

### Features Accessible via Docker

1. ✅ **NCF (NeuroLake Common Format)**
   - AI-native storage format
   - Automatic PII detection
   - Time travel & versioning
   - ACID transactions

2. ✅ **Cloud IAM Authentication**
   - AWS IAM Roles
   - Azure Managed Identity
   - GCP Workload Identity

3. ✅ **Data Catalog**
   - Unified catalog
   - Search & discovery
   - Metadata management

4. ✅ **NDM (NeuroLake Data Migration)**
   - Multi-platform SQL conversion
   - Migration assessment

5. ✅ **NUIC (Universal Integration Catalog)**
   - Cross-platform discovery
   - Schema mapping

6. ✅ **SQL Editor**
   - Query execution
   - Plan visualization
   - Query optimization

7. ✅ **Notebooks**
   - Interactive analysis
   - Code execution
   - Data exploration

8. ✅ **Workflows**
   - ETL pipelines
   - Orchestration

9. ✅ **Data Lineage**
   - Dependency tracking
   - Impact analysis

10. ✅ **Compliance**
    - GDPR/CCPA reporting
    - Policy management

---

## Deployment Files

### docker-compose.test.yml
**Purpose**: Quick testing deployment
**Services**: dashboard, postgres, redis, minio
**File**: Lightweight configuration for E2E testing

### Dockerfile.dashboard
**Purpose**: Build NeuroLake dashboard image
**Base**: python:3.11-slim
**Includes**:
- Dashboard application
- Test data
- Migration module
- Notebook system
- All NeuroLake packages

---

## Step-by-Step Deployment

### Step 1: Prerequisites

**Check Docker**:
```bash
docker --version
# Should show: Docker version 28.x or higher

docker ps
# Should show running containers or empty list (no errors)
```

**Required**:
- Docker Desktop for Windows
- At least 4GB RAM available
- At least 10GB disk space

### Step 2: Deploy Services

**Option A: Using Batch Script (Recommended)**:
```bash
cd C:\Users\techh\PycharmProjects\neurolake
docker-start-test.bat
```

**Option B: Manual Commands**:
```bash
# Stop existing containers
docker-compose -f docker-compose.test.yml down

# Build dashboard image
docker-compose -f docker-compose.test.yml build dashboard

# Start all services
docker-compose -f docker-compose.test.yml up -d

# Check status
docker-compose -f docker-compose.test.yml ps
```

### Step 3: Verify Deployment

**Check all services are healthy**:
```bash
docker-compose -f docker-compose.test.yml ps
```

**Expected output**:
```
NAME                    STATUS              PORTS
neurolake-dashboard     Up (healthy)        0.0.0.0:5000->5000/tcp
neurolake-postgres      Up (healthy)        0.0.0.0:5432->5432/tcp
neurolake-redis         Up (healthy)        0.0.0.0:6379->6379/tcp
neurolake-minio         Up (healthy)        0.0.0.0:9000-9001->9000-9001/tcp
```

### Step 4: Access Dashboard

Open browser to: **http://localhost:5000**

**Expected**:
- Dashboard loads successfully
- All navigation items visible
- No errors in browser console

---

## Testing via Docker

### Automated E2E Testing

```bash
# Run comprehensive E2E tests
python docker-test-e2e.py
```

**Tests performed**:
1. NCF tables (list, create, PII scan)
2. Cloud authentication (status, configure)
3. Catalog search
4. Data ingestion
5. SQL query execution
6. Data lineage
7. Schema evolution
8. Quality metrics
9. Notebooks

### Manual Testing

#### Test 1: NCF Tab
1. Open http://localhost:5000
2. Click "NCF Tables" in sidebar
3. Click "Create NCF Table"
4. Name: `employee`
5. Schema:
```json
{
  "emp_id": "int64",
  "emp_name": "string",
  "emp_email": "string",
  "emp_phone": "string",
  "ssn": "string"
}
```
6. Click "Scan All for PII"
7. **Expected**: 4 PII columns detected

#### Test 2: Cloud Auth Tab
1. Click "Cloud Auth" in sidebar
2. View AWS/Azure/GCP status
3. Click "Configure" on AWS
4. Enter region: `us-east-1`
5. **Expected**: Status updates

#### Test 3: SQL Editor
1. Click "SQL Editor" tab
2. Enter:
```sql
SELECT 'Docker Test' as message, CURRENT_TIMESTAMP as timestamp
```
3. Click "Execute"
4. **Expected**: Results displayed

---

## Accessing Services

### Dashboard
- **URL**: http://localhost:5000
- **Purpose**: Main UI for all features

### MinIO Console
- **URL**: http://localhost:9001
- **Username**: neurolake
- **Password**: dev_password
- **Purpose**: Object storage management

### PostgreSQL
- **Host**: localhost
- **Port**: 5432
- **Database**: neurolake
- **Username**: neurolake
- **Password**: dev_password
- **Purpose**: Metadata catalog

### Redis
- **Host**: localhost
- **Port**: 6379
- **Purpose**: Caching & sessions

---

## Viewing Logs

### Dashboard Logs
```bash
# Follow logs in real-time
docker-compose -f docker-compose.test.yml logs -f dashboard

# View last 100 lines
docker-compose -f docker-compose.test.yml logs --tail=100 dashboard
```

### All Services Logs
```bash
docker-compose -f docker-compose.test.yml logs -f
```

### Specific Service
```bash
# Postgres logs
docker-compose -f docker-compose.test.yml logs postgres

# Redis logs
docker-compose -f docker-compose.test.yml logs redis

# MinIO logs
docker-compose -f docker-compose.test.yml logs minio
```

---

## Troubleshooting

### Dashboard Won't Start

**Check logs**:
```bash
docker-compose -f docker-compose.test.yml logs dashboard
```

**Common issues**:
1. Port 5000 already in use
   ```bash
   # Find and kill process
   netstat -ano | findstr :5000
   taskkill /F /PID <pid>
   ```

2. Database not ready
   ```bash
   # Restart postgres
   docker-compose -f docker-compose.test.yml restart postgres
   ```

3. Out of memory
   ```bash
   # Check Docker resources
   docker stats
   # Increase memory in Docker Desktop settings
   ```

### Services Won't Start

**Reset everything**:
```bash
# Stop all containers
docker-compose -f docker-compose.test.yml down

# Remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.test.yml down -v

# Rebuild and restart
docker-compose -f docker-compose.test.yml build
docker-compose -f docker-compose.test.yml up -d
```

### Health Checks Failing

**Check individual service**:
```bash
# Execute health check manually
docker exec neurolake-dashboard curl -f http://localhost:5000/health
docker exec neurolake-postgres pg_isready -U neurolake
docker exec neurolake-redis redis-cli ping
docker exec neurolake-minio curl -f http://localhost:9000/minio/health/live
```

---

## Stopping Services

### Stop all containers
```bash
docker-compose -f docker-compose.test.yml stop
```

### Stop and remove containers
```bash
docker-compose -f docker-compose.test.yml down
```

### Stop and remove everything (including volumes)
```bash
docker-compose -f docker-compose.test.yml down -v
```

---

## Data Persistence

### What's Persistent

**Docker Volumes**:
- `postgres_test_data` - Database data
- `redis_test_data` - Redis data
- `minio_test_data` - Object storage

**Mounted Directories**:
- `./test_data_e2e` - Test data files
- `./catalog_data` - Catalog metadata
- `./logs` - Application logs

### Backup Data

```bash
# Backup postgres
docker exec neurolake-postgres pg_dump -U neurolake neurolake > backup.sql

# Backup volumes
docker run --rm -v postgres_test_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

---

## Performance Tuning

### Increase Resources

**In docker-compose.test.yml**, add to dashboard service:
```yaml
dashboard:
  ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

### Database Tuning

**Connect to postgres**:
```bash
docker exec -it neurolake-postgres psql -U neurolake
```

**Run optimizations**:
```sql
-- Analyze tables
ANALYZE;

-- Vacuum
VACUUM ANALYZE;
```

---

## Security Notes

### Default Passwords

**⚠️ WARNING**: Change default passwords in production!

Current defaults (for testing only):
- PostgreSQL: `dev_password`
- MinIO: `dev_password`
- Redis: No password (local only)

### Production Deployment

For production, update:
1. All passwords in `docker-compose.test.yml`
2. Enable SSL/TLS for all services
3. Configure firewall rules
4. Use secrets management
5. Enable audit logging

---

## Next Steps

### After Successful Deployment

1. ✅ Run E2E tests: `python docker-test-e2e.py`
2. ✅ Test all features manually
3. ✅ Load sample data from `test_data_e2e/`
4. ✅ Create test workflows
5. ✅ Verify PII detection
6. ✅ Test cloud auth configuration

### Moving to Production

1. Update `docker-compose.yml` (full deployment)
2. Configure environment variables
3. Set up SSL certificates
4. Configure backup strategy
5. Set up monitoring (Prometheus/Grafana)
6. Configure log aggregation
7. Set up alerting

---

## Quick Reference

### Essential Commands

```bash
# Start
docker-compose -f docker-compose.test.yml up -d

# Stop
docker-compose -f docker-compose.test.yml stop

# Restart
docker-compose -f docker-compose.test.yml restart

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Check status
docker-compose -f docker-compose.test.yml ps

# Rebuild
docker-compose -f docker-compose.test.yml build

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

### URLs

- Dashboard: http://localhost:5000
- MinIO Console: http://localhost:9001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

**Created**: January 8, 2025
**Status**: ✅ Ready for Docker Deployment
**Tested**: Windows Docker Desktop 28.3.0

---

**Happy Deploying!** 🐳
