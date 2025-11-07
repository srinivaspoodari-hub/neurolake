"""
NeuroLake Local Storage Initialization
Creates local-first storage structure on user's computer
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

def initialize_neurolake_storage(base_path=None):
    """
    Initialize NeuroLake local storage structure

    Args:
        base_path: Base directory for NeuroLake storage
                  Default: C:/NeuroLake (Windows) or ~/NeuroLake (Linux/Mac)
    """

    # Determine base path
    if base_path is None:
        if sys.platform == 'win32':
            base_path = "C:/NeuroLake"
        else:
            base_path = os.path.expanduser("~/NeuroLake")

    base_path = Path(base_path)

    print("="*80)
    print("NeuroLake Local Storage Initialization".center(80))
    print("="*80)
    print(f"\nBase Path: {base_path}")
    print(f"Platform: {sys.platform}")
    print()

    # Create directory structure
    directories = {
        'config': 'Configuration files',
        'catalog': 'Data catalog metadata',
        'buckets/raw-data': 'Landing zone for raw ingested data',
        'buckets/processed': 'Cleaned and transformed data',
        'buckets/analytics': 'Analytics-ready datasets',
        'buckets/ml-models': 'Machine learning models',
        'buckets/archive': 'Cold storage / archived data',
        'logs': 'Application and query logs',
        'cache': 'Query results cache',
        'temp': 'Temporary working directory',
    }

    print("[STEP 1] Creating Directory Structure")
    print("-" * 80)
    for dir_name, description in directories.items():
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_name.ljust(30)} - {description}")

    # Create default configuration
    print("\n[STEP 2] Creating Configuration Files")
    print("-" * 80)

    config = {
        'neurolake': {
            'version': '1.0.0',
            'initialized_at': datetime.now().isoformat(),
            'platform': sys.platform,
        },
        'storage': {
            'base_path': str(base_path),
            'local_capacity_gb': 100,
            'cloud_burst_enabled': True,
            'cloud_burst_threshold_percent': 80,
        },
        'buckets': {
            'raw-data': {
                'path': str(base_path / 'buckets/raw-data'),
                'tier': 'local',
                'retention_days': 90,
                'purpose': 'Landing zone for raw data ingestion',
                'auto_catalog': True,
            },
            'processed': {
                'path': str(base_path / 'buckets/processed'),
                'tier': 'local',
                'retention_days': 365,
                'purpose': 'Cleaned and transformed data',
                'auto_catalog': True,
            },
            'analytics': {
                'path': str(base_path / 'buckets/analytics'),
                'tier': 'local',
                'retention_days': 730,
                'purpose': 'Analytics-ready datasets',
                'auto_catalog': True,
            },
            'ml-models': {
                'path': str(base_path / 'buckets/ml-models'),
                'tier': 'local',
                'retention_days': -1,  # Keep forever
                'purpose': 'ML model storage',
                'auto_catalog': False,
            },
            'archive': {
                'path': str(base_path / 'buckets/archive'),
                'tier': 'cloud',  # Prefer cloud storage
                'retention_days': 1095,  # 3 years
                'purpose': 'Long-term cold storage',
                'auto_catalog': False,
            },
        },
        'catalog': {
            'storage_path': str(base_path / 'catalog'),
            'backend': 'json',  # json, sqlite, or postgresql
            'auto_lineage': True,
            'auto_schema_detection': True,
        },
        'hybrid_storage': {
            'local_threshold_gb': 80,
            'cloud_provider': 's3',  # s3, azure, or gcs
            'cloud_bucket': 'neurolake-cloud-burst',
            'cloud_region': 'us-east-1',
        },
        'monitoring': {
            'log_level': 'INFO',
            'log_path': str(base_path / 'logs'),
            'metrics_enabled': True,
            'audit_enabled': True,
        },
    }

    config_file = base_path / 'config/settings.yaml'
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"  [OK] Created: {config_file}")

    # Create README
    readme_content = f"""# NeuroLake Local Storage

This directory contains your NeuroLake data and configuration.

## Directory Structure

- **config/** - Configuration files
- **catalog/** - Data catalog metadata (tables, lineage, schemas)
- **buckets/** - Storage buckets for organizing your data:
  - `raw-data/` - Landing zone for ingested data
  - `processed/` - Cleaned and transformed data
  - `analytics/` - Analytics-ready datasets
  - `ml-models/` - Machine learning models
  - `archive/` - Long-term cold storage
- **logs/** - Application and query logs
- **cache/** - Query results cache
- **temp/** - Temporary working files

## Creating New Buckets

You can create new buckets through:
1. Dashboard UI: Storage & Buckets → Create New Bucket
2. API: POST /api/buckets/create
3. Manually: Create folder in `buckets/` and update config

## Backup

To backup your data, simply copy this entire folder:
```bash
# Windows
xcopy /E /I C:\\NeuroLake D:\\Backup\\NeuroLake

# Linux/Mac
cp -r ~/NeuroLake /backup/NeuroLake
```

## Cloud Burst

When local storage exceeds {config['storage']['cloud_burst_threshold_percent']}% capacity,
data will automatically tier to cloud storage ({config['hybrid_storage']['cloud_provider']}).

## Configuration

Edit `config/settings.yaml` to customize:
- Storage capacity limits
- Bucket retention policies
- Cloud burst settings
- Monitoring options

Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Platform: {sys.platform}
Base Path: {base_path}
"""

    readme_file = base_path / 'README.md'
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"  [OK] Created: {readme_file}")

    # Create .gitignore
    gitignore_content = """# NeuroLake Local Storage
cache/
temp/
logs/*.log
*.tmp
*.lock

# Keep structure but ignore large data files
buckets/*/*.ncf
buckets/*/*.parquet
buckets/*/*.csv

# Keep catalog metadata
!catalog/
catalog/*.json
"""

    gitignore_file = base_path / '.gitignore'
    with open(gitignore_file, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    print(f"  [OK] Created: {gitignore_file}")

    # Create sample data
    print("\n[STEP 3] Creating Sample Files")
    print("-" * 80)

    sample_catalog = base_path / 'catalog/sample_tables.json'
    with open(sample_catalog, 'w', encoding='utf-8') as f:
        f.write('{"tables": [], "initialized": true}\n')
    print(f"  [OK] Created: {sample_catalog}")

    # Create bucket info files
    for bucket_name in config['buckets'].keys():
        bucket_path = base_path / f'buckets/{bucket_name}'
        info_file = bucket_path / 'BUCKET_INFO.txt'
        bucket_config = config['buckets'][bucket_name]

        info_content = f"""Bucket: {bucket_name}
Purpose: {bucket_config['purpose']}
Tier: {bucket_config['tier']}
Retention: {bucket_config['retention_days']} days
Auto-catalog: {bucket_config['auto_catalog']}

You can store data files here. Supported formats:
- NCF (NeuroLake Columnar Format) - Recommended
- Parquet
- CSV
- JSON
- Avro

Files will be automatically:
- Indexed in the data catalog
- Tracked for lineage
- Monitored for size limits
- Tiered to cloud if needed
"""
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(info_content)
        print(f"  [OK] Created: {info_file}")

    # Summary
    print("\n" + "="*80)
    print("INITIALIZATION COMPLETE!".center(80))
    print("="*80)

    print(f"\n✅ NeuroLake storage initialized at: {base_path}")
    print(f"\n📁 You can now:")
    print(f"   1. Browse files in File Explorer/Finder: {base_path}")
    print(f"   2. Drag & drop data files into buckets")
    print(f"   3. Configure settings: {config_file}")
    print(f"   4. Start using NeuroLake dashboard")

    print(f"\n🚀 Next Steps:")
    print(f"   1. Update docker-compose.yml volume mounts:")
    print(f"      volumes:")
    print(f"        - {base_path}:/neurolake")
    print(f"   ")
    print(f"   2. Restart dashboard:")
    print(f"      docker-compose restart dashboard")
    print(f"   ")
    print(f"   3. Open dashboard and verify storage is visible")

    print(f"\n💡 Tip: Add files to buckets and they'll appear in the dashboard!")
    print(f"   Example: Copy a CSV file to {base_path}/buckets/raw-data/")
    print(f"            Dashboard will auto-detect and catalog it!")

    print("\n" + "="*80 + "\n")

    return str(base_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Initialize NeuroLake local storage')
    parser.add_argument('--path', type=str, default=None,
                       help='Base path for NeuroLake storage (default: C:/NeuroLake or ~/NeuroLake)')

    args = parser.parse_args()

    try:
        base_path = initialize_neurolake_storage(args.path)
        print(f"SUCCESS! Storage initialized at: {base_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
