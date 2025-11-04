# 🐳 Docker Quick Start Guide - NeuroLake Migration Module

## Prerequisites

1. **Docker Desktop** installed and running
   - Download: https://www.docker.com/products/docker-desktop
   - Ensure Docker is running (check system tray)

2. **Anthropic API Key**
   - Get your key from: https://console.anthropic.com/
   - Required for AI-powered migration features

---

## 🚀 Option 1: Quick Start (Migration Module Only)

### Step 1: Set Your API Key

**Windows (PowerShell)**:
```powershell
$env:ANTHROPIC_API_KEY="your-api-key-here"
```

**Windows (Command Prompt)**:
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

**Linux/Mac**:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Step 2: Launch Migration Dashboard

```bash
# Build and start the container
docker-compose -f docker-compose.migration.yml up --build

# Or run in detached mode (background)
docker-compose -f docker-compose.migration.yml up -d --build
```

### Step 3: Access Dashboard

Open your browser to:
```
http://localhost:8501
```

You'll see the **NeuroLake Migration Module** dashboard!

### Stop the Container

```bash
# Stop and remove containers
docker-compose -f docker-compose.migration.yml down

# Stop, remove, and clean volumes
docker-compose -f docker-compose.migration.yml down -v
```

---

## 🎯 Option 2: Full NeuroLake Platform

To run the complete platform with all services:

```bash
# Start all services (includes migration + advanced dashboard + databases)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Access Points**:
- Migration Dashboard: http://localhost:8501
- Advanced Dashboard: http://localhost:5000
- API: http://localhost:8000
- MinIO Console: http://localhost:9001
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090
- Temporal UI: http://localhost:8080

---

## 📋 Using .env File (Recommended)

### Step 1: Create .env file

```bash
# Copy example file
cp .env.example .env

# Or create manually
notepad .env  # Windows
nano .env     # Linux/Mac
```

### Step 2: Edit .env file

```env
# Add your API key
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Optional: Other settings
ENV=development
LOG_LEVEL=info
```

### Step 3: Launch (will auto-load .env)

```bash
docker-compose -f docker-compose.migration.yml up -d
```

---

## 🛠️ Troubleshooting

### Issue: Container won't start

**Solution 1: Check Docker is running**
```bash
docker info
```

**Solution 2: Check ports are available**
```bash
# Check if port 8501 is in use
netstat -ano | findstr :8501  # Windows
lsof -i :8501                  # Linux/Mac
```

**Solution 3: Rebuild image**
```bash
docker-compose -f docker-compose.migration.yml build --no-cache
docker-compose -f docker-compose.migration.yml up -d
```

### Issue: API Key not working

**Check environment variable**:
```bash
docker exec neurolake-migration env | grep ANTHROPIC
```

**Set it directly in docker-compose.migration.yml**:
```yaml
environment:
  - ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### Issue: Permission errors (Linux/Mac)

```bash
# Fix permissions
sudo chown -R $USER:$USER migration_module/uploads
sudo chmod -R 755 migration_module/uploads
```

### View Container Logs

```bash
# All logs
docker-compose -f docker-compose.migration.yml logs

# Follow logs (real-time)
docker-compose -f docker-compose.migration.yml logs -f migration

# Last 100 lines
docker-compose -f docker-compose.migration.yml logs --tail=100 migration
```

---

## 🔧 Advanced Docker Commands

### Build Only (No Start)
```bash
docker-compose -f docker-compose.migration.yml build
```

### Start Existing Container
```bash
docker-compose -f docker-compose.migration.yml start
```

### Stop Without Removing
```bash
docker-compose -f docker-compose.migration.yml stop
```

### Restart Container
```bash
docker-compose -f docker-compose.migration.yml restart
```

### Execute Commands Inside Container
```bash
# Open shell
docker exec -it neurolake-migration bash

# Run migration CLI
docker exec neurolake-migration python run_migration_module.py cli --help

# Check Python version
docker exec neurolake-migration python --version
```

### View Resource Usage
```bash
docker stats neurolake-migration
```

### Inspect Container
```bash
docker inspect neurolake-migration
```

---

## 💾 Data Persistence

Data is persisted in Docker volumes:
- `migration-uploads`: Uploaded source files
- `migration-data`: Converted code and results
- `migration-logs`: Application logs

### List Volumes
```bash
docker volume ls
```

### Inspect Volume
```bash
docker volume inspect neurolake_migration-uploads
```

### Backup Volume
```bash
# Create backup
docker run --rm -v neurolake_migration-uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /data

# Restore backup
docker run --rm -v neurolake_migration-uploads:/data -v $(pwd):/backup alpine tar xzf /backup/uploads-backup.tar.gz -C /
```

---

## 🎨 Customizing the Container

### Change Port

Edit `docker-compose.migration.yml`:
```yaml
ports:
  - "8502:8501"  # Access at http://localhost:8502
```

### Add More Memory

```yaml
services:
  migration:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### Mount Local Code (Development)

```yaml
volumes:
  - ./migration_module:/app/migration_module:ro  # Read-only
  - ./migration_module/uploads:/app/migration_module/uploads
```

---

## 📊 Docker Desktop Dashboard

1. Open **Docker Desktop**
2. Click **Containers** tab
3. See `neurolake-migration` container
4. Click container name for:
   - Logs
   - Stats (CPU, Memory)
   - Files
   - Terminal

---

## 🚀 Production Deployment

### Build for Production

```bash
# Build optimized image
docker build -f Dockerfile.migration -t neurolake-migration:prod .

# Tag for registry
docker tag neurolake-migration:prod your-registry.com/neurolake-migration:latest

# Push to registry
docker push your-registry.com/neurolake-migration:latest
```

### Production docker-compose

```yaml
services:
  migration:
    image: your-registry.com/neurolake-migration:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ENV=production
      - LOG_LEVEL=warning
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## 🧪 Testing the Setup

### Step 1: Check Container Health

```bash
docker-compose -f docker-compose.migration.yml ps
```

Should show:
```
NAME                  STATUS              PORTS
neurolake-migration   Up (healthy)        0.0.0.0:8501->8501/tcp
```

### Step 2: Check Logs

```bash
docker-compose -f docker-compose.migration.yml logs migration
```

Should see:
```
You can now view your Streamlit app in your browser.
Local URL: http://0.0.0.0:8501
```

### Step 3: Access Dashboard

Open: http://localhost:8501

You should see:
- 🏠 Platform Overview page
- Navigation menu with all features
- Metrics showing 22 source platforms

### Step 4: Test Upload

1. Go to **📤 Upload & Parse**
2. Upload a sample SQL file
3. Check parsing works
4. Verify AI features are available

---

## 📚 Next Steps

1. **Upload Code**: Try the 📤 Upload & Parse page
2. **Extract Logic**: Use 🧠 Logic Extraction
3. **Convert Code**: Try 🔄 SQL to SQL or ⚡ ETL to Spark
4. **Try NeuroLake**: Use 🆕 Migrate to NeuroLake

---

## 💡 Tips

1. **Keep Docker Desktop Running**: Required for containers to work
2. **Set API Key**: Required for AI features to function
3. **Check Logs**: Use `docker-compose logs -f` to debug issues
4. **Restart if Needed**: `docker-compose restart` fixes most issues
5. **Clean Build**: Use `--build --no-cache` for fresh start

---

## 🔗 Quick Reference

### One-Line Launchers

**Windows PowerShell**:
```powershell
$env:ANTHROPIC_API_KEY="your-key"; docker-compose -f docker-compose.migration.yml up -d
```

**Windows Command Prompt**:
```cmd
set ANTHROPIC_API_KEY=your-key && docker-compose -f docker-compose.migration.yml up -d
```

**Linux/Mac**:
```bash
ANTHROPIC_API_KEY="your-key" docker-compose -f docker-compose.migration.yml up -d
```

### Access URLs

| Service | URL | Description |
|---------|-----|-------------|
| Migration Dashboard | http://localhost:8501 | Main migration interface |
| Health Check | http://localhost:8501/_stcore/health | Container health |

---

## ❓ FAQ

**Q: Do I need Python installed?**
A: No! Docker includes everything.

**Q: Can I run without Docker?**
A: Yes, use: `python run_migration_module.py`

**Q: How do I update to latest version?**
A: Run:
```bash
git pull
docker-compose -f docker-compose.migration.yml up -d --build
```

**Q: How much disk space needed?**
A: ~2-3 GB for Docker images + your data

**Q: Can I run on Windows?**
A: Yes! Docker Desktop works on Windows 10/11

---

## 🎉 Success!

If you see the dashboard at http://localhost:8501, you're all set!

**Welcome to NeuroLake Migration Module!** 🚀

Start migrating your legacy code to modern platforms with AI assistance!
