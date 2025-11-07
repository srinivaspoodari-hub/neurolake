# Data Catalog Integration Issue - Root Cause Analysis

**Date**: 2025-11-05
**Issue**: Data Catalog tab in dashboard shows no data

---

## 🔴 Root Cause Identified

The catalog modules work perfectly in isolation (proven by 16,927 bytes of test data), but the dashboard cannot see the data due to **Docker volume mounting issues**.

### The Problem Chain

1. **Dashboard runs in Docker container** (`neurolake-dashboard`)
2. **Volume is mounted**: `./data:/data` in `docker-compose.yml`
3. **BUT**: The `./data` directory didn't exist when containers were first created
4. **Result**: The `/data` mount point in the container is empty or doesn't exist
5. **Code tries to write to**: `/data/catalog/`, `/data/lineage/`, etc.
6. **But these directories don't exist in the container**
7. **So catalog remains empty**

### Evidence

```bash
# Host has data
$ ls data/catalog
catalog.json (18 assets, 5 tables)

# Container doesn't have /data mounted
$ docker exec neurolake-dashboard ls /data
ls: cannot access '/data': No such file or directory

# API returns empty
$ curl http://localhost:5000/api/catalog/stats
{"status":"success","stats":{"total_assets":0,"by_type":{},"total_tags":0}}
```

---

## ✅ Solution

### Option 1: Fix Volume Mount (RECOMMENDED)

1. **Stop all containers**:
   ```bash
   docker-compose down
   ```

2. **Ensure `./data` directory exists with proper structure**:
   ```bash
   mkdir -p data/catalog data/lineage data/schemas data/metadata data/transformations
   ```

3. **Populate with sample data**:
   ```bash
   python populate_dashboard_catalog.py
   ```

4. **Start containers** (will mount existing `./data`):
   ```bash
   docker-compose up -d --build
   ```

5. **Verify**:
   ```bash
   curl http://localhost:5000/api/catalog/stats
   # Should show: {"total_assets": 18, ...}
   ```

### Option 2: Use API to Populate (ALTERNATIVE)

Instead of pre-populating files, register tables via the dashboard API after it starts:

```bash
curl -X POST http://localhost:5000/api/catalog/table/register \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "customers",
    "database": "production",
    "schema": "public",
    "columns": [
      {"name": "customer_id", "type": "int"},
      {"name": "email", "type": "string"}
    ],
    "description": "Customer data",
    "tags": ["production"]
  }'
```

---

## 📋 Verification Checklist

After applying the solution:

- [ ] `./data/` directory exists on host
- [ ] `./data/catalog/catalog.json` exists and has content
- [ ] Dashboard container has `/data` mounted: `docker exec neurolake-dashboard ls /data`
- [ ] API returns data: `curl http://localhost:5000/api/catalog/stats`
- [ ] Dashboard UI shows tables in "All Assets" tab
- [ ] "Lineage" tab shows relationships
- [ ] "Schemas" tab shows schema versions
- [ ] "Transformations" tab shows captured transformations

---

## 🎯 Next Steps

1. **Immediate**: Fix volume mount and populate catalog
2. **Short-term**: Create initialization script that runs on container startup
3. **Long-term**: Use PostgreSQL instead of JSON files for catalog storage

---

## 📝 Related Files

- `advanced_databricks_dashboard.py:3503-3512` - Catalog initialization
- `docker-compose.yml:123-126` - Volume mounts
- `populate_dashboard_catalog.py` - Sample data population script

---

## 💡 Lessons Learned

1. **Docker volumes must exist before mounting** - Empty directories won't create properly
2. **Test integration, not just modules** - Modules worked, integration didn't
3. **Verify container filesystem** - Don't assume mounts work
4. **Use persistent storage** - JSON files in containers are ephemeral without volumes

---

**Status**: 🔴 **BLOCKED** - Requires Docker restart with proper volume mounts
**Priority**: **CRITICAL** - Dashboard appears empty to users
**Est. Fix Time**: 10 minutes
