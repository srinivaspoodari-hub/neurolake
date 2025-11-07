# NeuroLake Local-First Storage - Proper Architecture

**Date**: 2025-11-05
**Issue**: Current implementation uses Docker volumes instead of local computer storage
**Impact**: **CRITICAL** - Violates local-first design principle

---

## 🔴 Current Problem

### What's Wrong:
```yaml
# docker-compose.yml
volumes:
  - ./data:/data    # Hidden in Docker, not truly local
  - postgres_data:  # Docker volume, not accessible
  - minio_data:     # Docker volume, not accessible
```

**Problems**:
1. ❌ Data stored in Docker volumes - hidden from user
2. ❌ Can't browse files in Windows Explorer
3. ❌ Not truly "local-first"
4. ❌ If Docker is removed, data is lost
5. ❌ Can't easily backup/sync data
6. ❌ No multi-bucket support

---

## ✅ Correct Local-First Architecture

### Storage Location (User's Computer):

```
C:\NeuroLake\                          (or ~/NeuroLake/ on Linux/Mac)
├── config\
│   ├── settings.yaml                  # User configuration
│   └── buckets.yaml                   # Bucket definitions
│
├── catalog\                           # Data Catalog metadata
│   ├── tables.json
│   ├── lineage.json
│   └── schemas.json
│
├── buckets\                           # User-created storage buckets
│   ├── raw-data\                      # Landing zone for raw data
│   │   ├── customers\
│   │   │   └── customers.ncf
│   │   └── orders\
│   │       └── orders.ncf
│   │
│   ├── processed\                     # Cleaned/transformed data
│   │   └── customer_summary\
│   │       └── customer_summary.ncf
│   │
│   ├── analytics\                     # Analytics-ready data
│   │   └── dashboards\
│   │
│   ├── ml-models\                     # ML model storage
│   │   ├── churn-prediction\
│   │   └── customer-segmentation\
│   │
│   └── archive\                       # Cold storage
│       └── 2023\
│
├── logs\                              # Application logs
│   ├── query.log
│   ├── error.log
│   └── audit.log
│
└── cache\                             # Local cache
    └── query-results\
```

**Benefits**:
✅ User can see all files in Windows Explorer
✅ Easy backup (just copy C:\NeuroLake\)
✅ Easy sharing (send folder to colleague)
✅ Multi-bucket support for organization
✅ Survives Docker restarts
✅ True local-first architecture

---

## 🎯 Implementation Plan

### 1. Update docker-compose.yml

```yaml
services:
  dashboard:
    volumes:
      # Mount user's local NeuroLake directory
      - C:/NeuroLake:/neurolake          # Windows
      # - ~/NeuroLake:/neurolake         # Linux/Mac

      # Individual mounts for clarity
      - C:/NeuroLake/catalog:/neurolake/catalog
      - C:/NeuroLake/buckets:/neurolake/buckets
      - C:/NeuroLake/logs:/neurolake/logs
      - C:/NeuroLake/cache:/neurolake/cache
```

### 2. Create Initialization Script

**`initialize_local_storage.py`**:
```python
import os
from pathlib import Path

def initialize_neurolake_storage(base_path="C:/NeuroLake"):
    """Initialize NeuroLake local storage structure"""

    # Create directory structure
    directories = [
        f"{base_path}/config",
        f"{base_path}/catalog",
        f"{base_path}/buckets/raw-data",
        f"{base_path}/buckets/processed",
        f"{base_path}/buckets/analytics",
        f"{base_path}/buckets/ml-models",
        f"{base_path}/buckets/archive",
        f"{base_path}/logs",
        f"{base_path}/cache",
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Created: {dir_path}")

    # Create default config
    config = f"""
# NeuroLake Configuration
storage:
  base_path: {base_path}
  local_capacity_gb: 100
  cloud_burst_enabled: true

buckets:
  raw-data:
    path: {base_path}/buckets/raw-data
    tier: local
    retention_days: 90

  processed:
    path: {base_path}/buckets/processed
    tier: local
    retention_days: 365

  analytics:
    path: {base_path}/buckets/analytics
    tier: local
    retention_days: 730

  ml-models:
    path: {base_path}/buckets/ml-models
    tier: local
    retention_days: -1  # Keep forever

  archive:
    path: {base_path}/buckets/archive
    tier: cloud  # Auto-move to cloud
    retention_days: 1095  # 3 years

catalog:
  storage_path: {base_path}/catalog
  backend: json  # Can be: json, sqlite, postgresql

hybrid_storage:
  local_threshold_gb: 80  # When to burst to cloud
  cloud_provider: s3  # s3, azure, gcs
  cloud_bucket: neurolake-cloud-burst
"""

    with open(f"{base_path}/config/settings.yaml", 'w') as f:
        f.write(config)

    print(f"\n✅ NeuroLake storage initialized at: {base_path}")
    print(f"✅ You can now browse files in: {base_path}")
    print(f"✅ Config file: {base_path}/config/settings.yaml")
```

### 3. Update Dashboard to Use Local Storage

**`advanced_databricks_dashboard.py`** changes:
```python
import os
import yaml

# Load config from local storage
NEUROLAKE_HOME = os.environ.get('NEUROLAKE_HOME', 'C:/NeuroLake')

with open(f'{NEUROLAKE_HOME}/config/settings.yaml') as f:
    config = yaml.safe_load(f)

# Initialize catalog with local storage
catalog = DataCatalog(
    storage_path=f"{NEUROLAKE_HOME}/catalog"
)

# Initialize hybrid storage with buckets
hybrid_storage = HybridStorageManager(
    local_path=f"{NEUROLAKE_HOME}/buckets",
    cloud_path="s3://neurolake-cloud-burst",
    local_capacity_gb=config['storage']['local_capacity_gb']
)
```

---

## 🪣 Multi-Bucket Support

### Bucket Management API

```python
class BucketManager:
    """Manage user-created storage buckets"""

    def create_bucket(self, name, purpose, tier='local'):
        """Create a new storage bucket"""
        bucket_path = f"{NEUROLAKE_HOME}/buckets/{name}"
        os.makedirs(bucket_path, exist_ok=True)

        # Register in config
        self.config['buckets'][name] = {
            'path': bucket_path,
            'tier': tier,
            'created_at': datetime.now().isoformat(),
            'purpose': purpose
        }

        return bucket_path

    def list_buckets(self):
        """List all buckets"""
        return self.config['buckets']

    def get_bucket_stats(self, name):
        """Get bucket statistics"""
        path = self.config['buckets'][name]['path']
        total_size = sum(
            os.path.getsize(f)
            for f in Path(path).rglob('*')
            if f.is_file()
        )
        file_count = len(list(Path(path).rglob('*')))

        return {
            'size_gb': total_size / (1024**3),
            'file_count': file_count,
            'path': path
        }
```

### Dashboard UI - Bucket Browser

```html
<div class="bucket-browser">
  <h3>Storage Buckets</h3>

  <div class="bucket-list">
    <div class="bucket-card">
      <h4>raw-data</h4>
      <p>Landing zone for ingested data</p>
      <div class="bucket-stats">
        <span>12.5 GB</span>
        <span>1,234 files</span>
        <span>Tier: LOCAL</span>
      </div>
      <button onclick="browseBucket('raw-data')">Browse Files</button>
    </div>

    <div class="bucket-card">
      <h4>processed</h4>
      <p>Cleaned and transformed data</p>
      <div class="bucket-stats">
        <span>8.2 GB</span>
        <span>567 files</span>
        <span>Tier: LOCAL</span>
      </div>
      <button onclick="browseBucket('processed')">Browse Files</button>
    </div>

    <!-- More buckets... -->
  </div>

  <button onclick="createNewBucket()">+ Create New Bucket</button>
</div>
```

---

## 📊 Benefits of Local-First Storage

| Aspect | Docker Volumes | Local Storage | Winner |
|--------|---------------|---------------|--------|
| **User Access** | Hidden | Windows Explorer | ✅ Local |
| **Backup** | Complex | Copy folder | ✅ Local |
| **Portability** | Container-locked | Easily moved | ✅ Local |
| **Debugging** | Can't inspect | Direct access | ✅ Local |
| **Cost** | N/A | Free local disk | ✅ Local |
| **Speed** | Container overhead | Native FS | ✅ Local |
| **Sharing** | Export required | Share folder | ✅ Local |

---

## 🚀 Migration Steps

### For Existing Users:

1. **Run initialization**:
   ```bash
   python initialize_local_storage.py
   ```

2. **Copy existing data**:
   ```bash
   # Copy from Docker volumes to local
   docker cp neurolake-dashboard:/data C:/NeuroLake/
   ```

3. **Update docker-compose.yml**:
   ```yaml
   volumes:
     - C:/NeuroLake:/neurolake
   ```

4. **Restart containers**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

5. **Verify**:
   - Open Windows Explorer → C:\NeuroLake
   - Should see all folders and files
   - Dashboard should show data

---

## 🎯 Example User Workflow

### Data Engineer Creates New Bucket:

```bash
# 1. Open Dashboard
http://localhost:5000

# 2. Navigate to "Storage & Buckets"
Click "Create New Bucket"

# 3. Fill form:
Name: customer-analytics
Purpose: Customer behavior analysis
Tier: LOCAL
Retention: 365 days

# 4. Bucket created at:
C:\NeuroLake\buckets\customer-analytics\

# 5. User can now:
- Drag files into folder (Windows Explorer)
- Or upload via Dashboard UI
- Or use API: POST /api/buckets/customer-analytics/upload

# 6. Files automatically:
- Indexed in catalog
- Tracked for lineage
- Monitored for size (burst to cloud if needed)
```

---

## 💡 Key Insights

1. **Local-First is Not Just a Buzzword** - It means users own their data on their computers
2. **Docker Volumes Defeat the Purpose** - Hides data from users
3. **Multi-Bucket Organization** - Users need flexibility to organize data their way
4. **Easy Backup & Portability** - Just copy/sync the NeuroLake folder
5. **No Vendor Lock-In** - Data is in standard formats on user's disk

---

## 📋 Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Computer                          │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  C:\NeuroLake\  (USER ACCESSIBLE)                     │ │
│  │                                                        │ │
│  │  ├── buckets\                                         │ │
│  │  │   ├── raw-data\        (Browse in Explorer)       │ │
│  │  │   ├── processed\       (Drag & drop files)        │ │
│  │  │   └── analytics\       (Easy backup)              │ │
│  │                                                        │ │
│  │  ├── catalog\              (Metadata)                 │ │
│  │  │   ├── tables.json                                  │ │
│  │  │   └── lineage.json                                 │ │
│  │                                                        │ │
│  │  └── logs\                 (Audit trail)              │ │
│  └───────────────────────────────────────────────────────┘ │
│                          ↕                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │   Docker Container (Dashboard)                        │ │
│  │   Volume Mount: C:\NeuroLake:/neurolake              │ │
│  └───────────────────────────────────────────────────────┘ │
│                          ↕                                  │
│                   (When local full)                         │
│                          ↕                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │   Cloud Storage (Burst)                               │ │
│  │   S3 / Azure / GCS                                    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Action Items

- [ ] Create `initialize_local_storage.py`
- [ ] Update `docker-compose.yml` with local paths
- [ ] Add `BucketManager` class
- [ ] Add "Storage & Buckets" tab to dashboard
- [ ] Update catalog to use `C:\NeuroLake\catalog`
- [ ] Test: Browse files in Windows Explorer
- [ ] Test: Drag-drop files into buckets
- [ ] Test: Cloud burst when local is full
- [ ] Document for users

---

**Status**: 🔴 **NEEDS IMMEDIATE FIX**
**Priority**: **CRITICAL** - Core architectural issue
**Impact**: Violates local-first design, poor user experience
**Est. Fix Time**: 4 hours
