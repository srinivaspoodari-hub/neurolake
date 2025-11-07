# NeuroLake Dashboard - Launch Instructions

## ✅ Status: App is Running!

All services are deployed and healthy in Docker Desktop.

## How to Access

### Option 1: Open in Windows Browser (Recommended)

Open your web browser (Chrome, Edge, Firefox) and go to:

```
http://localhost:5000
```

Or try:
```
http://127.0.0.1:5000
```

### Option 2: Open from Command Line

Run this in Windows PowerShell or Command Prompt:
```powershell
start http://localhost:5000
```

Or in WSL/Git Bash:
```bash
cmd.exe /c start http://localhost:5000
```

### Option 3: Check Docker Desktop

1. Open **Docker Desktop** application
2. Go to **Containers** tab
3. Find `neurolake-dashboard` container
4. Click on it
5. Click **Open in Browser** button (if available)
6. Or copy the port link: `localhost:5000`

## Available URLs

Once in your browser, you can access:

### Main Dashboard
```
http://localhost:5000/
```

### Notebooks System
```
http://localhost:5000/notebook
```

### Migration Module
```
http://localhost:5000/migration
```

### Health Check
```
http://localhost:5000/health
```

## Verify Services

Run this command to check all services are healthy:
```bash
docker-compose ps
```

You should see:
- ✅ neurolake-dashboard (healthy)
- ✅ neurolake-postgres-1 (healthy)
- ✅ neurolake-redis-1 (healthy)
- ✅ neurolake-minio-1 (healthy)

## Troubleshooting

### If browser says "Can't connect"

1. **Check Docker Desktop is running**
   - Open Docker Desktop app
   - Ensure it says "Docker Desktop is running"

2. **Restart the dashboard**
   ```bash
   docker-compose restart dashboard
   ```

3. **Check logs**
   ```bash
   docker-compose logs dashboard --tail=50
   ```

   You should see:
   - `Application startup complete`
   - `Notebook API loaded successfully`
   - `All components initialized successfully`

4. **Check port is not in use**
   ```bash
   netstat -ano | findstr :5000
   ```

5. **Try different port** (if 5000 is blocked)
   Edit docker-compose.yml and change:
   ```yaml
   ports:
     - "8080:5000"  # Use 8080 instead
   ```
   Then: `docker-compose up -d dashboard`
   Access at: `http://localhost:8080`

### If you see empty page

- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private window
- Try different browser

## Quick Commands

### View logs
```bash
docker-compose logs -f dashboard
```

### Restart dashboard
```bash
docker-compose restart dashboard
```

### Stop all services
```bash
docker-compose down
```

### Start all services
```bash
docker-compose up -d
```

## System Requirements

- Docker Desktop must be running
- Port 5000 must be available
- At least 4GB RAM allocated to Docker
- Windows 10/11 with WSL2

## Contact

If you're still having issues, provide the output of:
```bash
docker-compose ps
docker-compose logs dashboard --tail=20
curl -I http://localhost:5000/health
```