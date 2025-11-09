# NeuroLake Backup Scripts

Comprehensive backup automation for NeuroLake platform.

## Overview

Three main backup scripts:

1. **`backup_database.py`** - PostgreSQL database backups
2. **`backup_storage.py`** - MinIO/S3 object storage backups
3. **`backup_scheduler.py`** - Automated backup orchestration

## Prerequisites

### Database Backups
- `pg_dump` and `psql` installed and available in PATH
- PostgreSQL client tools version 12+

### Storage Backups
- Python `minio` package: `pip install minio`

### General
- Python 3.8+
- Configured `.env` file with database and storage credentials

## Database Backup Usage

### Create Full Backup
```bash
python scripts/backup_database.py backup --type full
```

### Create Schema-Only Backup
```bash
python scripts/backup_database.py backup --type schema
```

### Create Data-Only Backup
```bash
python scripts/backup_database.py backup --type data
```

### List Available Backups
```bash
python scripts/backup_database.py list
```

### Restore from Backup
```bash
python scripts/backup_database.py restore --backup-file backups/neurolake_full_20250108_120000.sql.gz
```

### Cleanup Old Backups
```bash
python scripts/backup_database.py cleanup --retention-days 30
```

### Advanced Options
```bash
# Custom backup directory
python scripts/backup_database.py backup --backup-dir /mnt/backups

# Disable compression
python scripts/backup_database.py backup --no-compress

# Custom retention period
python scripts/backup_database.py backup --retention-days 60
```

## Storage Backup Usage

### Backup Single Bucket
```bash
python scripts/backup_storage.py backup --bucket data
```

### Backup All Buckets
```bash
python scripts/backup_storage.py backup --all
```

### List Available Backups
```bash
python scripts/backup_storage.py list
```

### Restore Bucket
```bash
python scripts/backup_storage.py restore \
    --backup-file backups/storage/storage_data_20250108_120000.tar.gz \
    --bucket data
```

### Restore with Overwrite
```bash
python scripts/backup_storage.py restore \
    --backup-file backups/storage/storage_data_20250108_120000.tar.gz \
    --bucket data \
    --overwrite
```

### Cleanup Old Backups
```bash
python scripts/backup_storage.py cleanup --retention-days 30
```

## Automated Backups

### Run All Backups
```bash
python scripts/backup_scheduler.py run
```

### Run Only Database Backup
```bash
python scripts/backup_scheduler.py database
```

### Run Only Storage Backup
```bash
python scripts/backup_scheduler.py storage
```

### With Email Notifications
```bash
python scripts/backup_scheduler.py run \
    --email \
    --recipients admin@example.com ops@example.com
```

## Scheduling

### Linux/macOS (cron)

Edit crontab:
```bash
crontab -e
```

Add daily backups at 2 AM:
```cron
# Daily full backup at 2 AM
0 2 * * * cd /path/to/neurolake && /usr/bin/python3 scripts/backup_scheduler.py run >> /var/log/neurolake_backup.log 2>&1

# Weekly cleanup on Sundays at 3 AM
0 3 * * 0 cd /path/to/neurolake && /usr/bin/python3 scripts/backup_database.py cleanup >> /var/log/neurolake_cleanup.log 2>&1
```

### Windows (Task Scheduler)

Create scheduled task:
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts\backup_scheduler.py run" -WorkingDirectory "C:\path\to\neurolake"

$Trigger = New-ScheduledTaskTrigger -Daily -At 2am

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "NeuroLake Daily Backup" -Action $Action -Trigger $Trigger -Principal $Principal
```

### Docker

Add to `docker-compose.yml`:
```yaml
services:
  backup:
    image: python:3.11
    volumes:
      - ./:/app
      - ./backups:/backups
    working_dir: /app
    command: python scripts/backup_scheduler.py run
    environment:
      - NEUROLAKE_DATABASE__HOST=postgres
      - NEUROLAKE_DATABASE__PORT=5432
      - NEUROLAKE_DATABASE__USERNAME=neurolake
      - NEUROLAKE_DATABASE__PASSWORD=${DB_PASSWORD}
      - NEUROLAKE_STORAGE__ENDPOINT=minio:9000
      - NEUROLAKE_STORAGE__ACCESS_KEY=${MINIO_ACCESS_KEY}
      - NEUROLAKE_STORAGE__SECRET_KEY=${MINIO_SECRET_KEY}
    depends_on:
      - postgres
      - minio
```

### Kubernetes (CronJob)

Create `backup-cronjob.yaml`:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neurolake-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: neurolake:latest
            command:
            - python
            - scripts/backup_scheduler.py
            - run
            env:
            - name: NEUROLAKE_DATABASE__HOST
              value: "postgres-service"
            - name: NEUROLAKE_DATABASE__PASSWORD
              valueFrom:
                secretKeyRef:
                  name: neurolake-secrets
                  key: db-password
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Backup Storage

### Recommended Storage Locations

**Development:**
- Local directory: `./backups`

**Production:**
- Network-attached storage (NAS)
- Cloud storage (S3, Azure Blob, GCS)
- Dedicated backup server
- Off-site backup location

### Backup Retention Strategy

**Recommended retention policy:**
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months
- Yearly backups: 7 years (if required for compliance)

Implement with multiple backup jobs:
```bash
# Daily backup (7-day retention)
0 2 * * * python scripts/backup_scheduler.py run --retention-days 7

# Weekly backup (28-day retention) - Sundays only
0 3 * * 0 python scripts/backup_scheduler.py run --retention-days 28

# Monthly backup (365-day retention) - 1st of month only
0 4 1 * * python scripts/backup_scheduler.py run --retention-days 365
```

## Monitoring

### Check Backup Status
```bash
# List recent backups
python scripts/backup_database.py list | tail -10
python scripts/backup_storage.py list | tail -10
```

### Verify Backup Integrity
```bash
# Test database backup restoration (non-destructive)
python scripts/backup_database.py restore \
    --backup-file backups/database/neurolake_full_YYYYMMDD_HHMMSS.sql.gz \
    --verify-only  # Note: implement this flag for verification
```

### Alerting

Configure email notifications:
```bash
# In production, configure SMTP settings in backup_scheduler.py
python scripts/backup_scheduler.py run \
    --email \
    --recipients dba@example.com devops@example.com
```

Set up external monitoring:
- Check backup file timestamps
- Monitor backup directory size
- Alert on backup failures

## Recovery

### Database Recovery

**Full database restore:**
```bash
# 1. Stop application
systemctl stop neurolake

# 2. Backup current database (just in case)
python scripts/backup_database.py backup --type full

# 3. Restore from backup
python scripts/backup_database.py restore \
    --backup-file backups/database/neurolake_full_20250108_020000.sql.gz

# 4. Verify restoration
psql -h localhost -U neurolake -d neurolake -c "SELECT COUNT(*) FROM users;"

# 5. Restart application
systemctl start neurolake
```

**Point-in-time recovery (if WAL archiving enabled):**
```bash
# Restore to specific time
pg_restore --host=localhost --port=5432 --username=neurolake \
    --dbname=neurolake --point-in-time-recovery="2025-01-08 14:30:00"
```

### Storage Recovery

**Restore bucket:**
```bash
# Restore data bucket
python scripts/backup_storage.py restore \
    --backup-file backups/storage/storage_data_20250108_020000.tar.gz \
    --bucket data \
    --overwrite
```

## Security

### Backup Encryption

**Encrypt backups:**
```bash
# Encrypt with GPG
gpg --symmetric --cipher-algo AES256 \
    backups/database/neurolake_full_20250108_020000.sql.gz

# Decrypt
gpg --decrypt \
    backups/database/neurolake_full_20250108_020000.sql.gz.gpg > backup.sql.gz
```

**Encrypt storage backups:**
```bash
# Encrypt tar.gz
openssl enc -aes-256-cbc -salt \
    -in backups/storage/storage_data_20250108_020000.tar.gz \
    -out backups/storage/storage_data_20250108_020000.tar.gz.enc

# Decrypt
openssl enc -aes-256-cbc -d \
    -in backups/storage/storage_data_20250108_020000.tar.gz.enc \
    -out backup.tar.gz
```

### Access Control

**Restrict backup file permissions:**
```bash
chmod 600 backups/database/*
chmod 600 backups/storage/*
chown postgres:postgres backups/database/
chown minio:minio backups/storage/
```

### Secure Storage

- Store backups on encrypted filesystems
- Use dedicated backup accounts with minimal privileges
- Implement backup file rotation and retention policies
- Store off-site copies for disaster recovery
- Regularly test backup restoration procedures

## Troubleshooting

### Common Issues

**1. pg_dump not found:**
```bash
# Install PostgreSQL client tools
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# macOS
brew install postgresql
```

**2. Permission denied:**
```bash
# Ensure backup directory is writable
chmod 755 backups/
chown $USER:$USER backups/
```

**3. MinIO connection failed:**
```bash
# Verify MinIO is running
mc admin info myminio

# Check credentials in .env file
cat .env | grep NEUROLAKE_STORAGE
```

**4. Backup file too large:**
```bash
# Use compression (enabled by default)
# Or split large backups
python scripts/backup_database.py backup --type data  # Data only
python scripts/backup_database.py backup --type schema  # Schema only
```

**5. Restore failed:**
```bash
# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log

# Verify backup file integrity
gunzip -t backups/database/neurolake_full_*.sql.gz
```

## Best Practices

1. **Test restorations regularly** - Verify backups can be restored
2. **Monitor backup size** - Track growth trends
3. **Implement 3-2-1 rule** - 3 copies, 2 different media, 1 off-site
4. **Automate backup verification** - Regular integrity checks
5. **Document recovery procedures** - Keep runbook updated
6. **Encrypt sensitive backups** - Protect PII and credentials
7. **Monitor backup jobs** - Alert on failures
8. **Version control backup scripts** - Track changes to automation
9. **Regular backup audits** - Review retention and coverage
10. **Disaster recovery drills** - Practice full system recovery

## Support

For issues or questions:
- Check logs: `tail -f /var/log/neurolake_backup.log`
- Review backup scripts: `scripts/backup_*.py`
- Contact: DevOps team
