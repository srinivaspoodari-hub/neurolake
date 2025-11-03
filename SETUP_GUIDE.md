# NeuroLake Development Environment Setup Guide

**System**: Windows 11
**Location**: C:\Users\techh\PycharmProjects\neurolake
**Date**: October 2024

---

## ✅ Task 001: Python 3.11+ - COMPLETED

**Status**: ✅ Already installed
**Version**: Python 3.13.5
**Location**: Check with `where python`

```powershell
# Verify
python --version
# Output: Python 3.13.5 ✓
```

---

## 🔄 Task 002: Install Java 11+ (Required for PySpark)

**Status**: ⬜ Not installed
**Required Version**: Java 11 or higher (recommend Java 17 LTS)

### Installation Steps (Windows)

#### Option 1: Using winget (Recommended)

Open **PowerShell as Administrator** and run:

```powershell
# Install OpenJDK 17 (LTS)
winget install Microsoft.OpenJDK.17

# Or install Oracle JDK 17
winget install Oracle.JDK.17
```

#### Option 2: Manual Installation

1. Download OpenJDK 17:
   - Go to: https://adoptium.net/
   - Download: Windows x64 installer
   - Version: OpenJDK 17 (LTS)

2. Run the installer:
   - Check "Set JAVA_HOME variable"
   - Check "Add to PATH"
   - Install to: `C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot\`

3. Verify installation:

```powershell
# Check Java version
java -version
# Expected: openjdk version "17.0.x"

# Check JAVA_HOME
echo $env:JAVA_HOME
# Expected: C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot
```

### If JAVA_HOME is not set:

```powershell
# Set JAVA_HOME (PowerShell)
[System.Environment]::SetEnvironmentVariable('JAVA_HOME', 'C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot', [System.EnvironmentVariableTarget]::Machine)

# Add to PATH
$javaPath = "$env:JAVA_HOME\bin"
$currentPath = [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::Machine)
[System.Environment]::SetEnvironmentVariable('Path', "$currentPath;$javaPath", [System.EnvironmentVariableTarget]::Machine)

# Restart terminal and verify
java -version
```

---

## 🔄 Task 003: Install Docker Desktop

**Status**: ⬜ Pending

### Installation Steps

1. **Download Docker Desktop for Windows**:
   - Go to: https://www.docker.com/products/docker-desktop/
   - Download: Docker Desktop for Windows
   - File: Docker Desktop Installer.exe

2. **Install**:
   - Run installer as Administrator
   - Enable WSL 2 (recommended)
   - Complete installation
   - Restart computer if prompted

3. **Start Docker Desktop**:
   - Open Docker Desktop
   - Wait for "Docker Desktop is running" status
   - Accept license if prompted

4. **Verify Installation**:

```bash
# Check Docker version
docker --version
# Expected: Docker version 24.0.x

# Check Docker is running
docker ps
# Expected: Empty list (no errors)

# Test Docker
docker run hello-world
# Expected: "Hello from Docker!" message
```

### Enable WSL 2 (if not already)

```powershell
# Run in PowerShell as Administrator
wsl --install

# Set WSL 2 as default
wsl --set-default-version 2

# Restart computer
```

---

## 🔄 Task 004: Install Kubernetes (minikube)

**Status**: ⬜ Pending

### Installation Steps

#### Option 1: Using winget (Recommended)

```powershell
# Install minikube
winget install Kubernetes.minikube

# Install kubectl
winget install Kubernetes.kubectl
```

#### Option 2: Manual Installation

1. **Download minikube**:
   - Go to: https://minikube.sigs.k8s.io/docs/start/
   - Download: Windows installer (AMD64)

2. **Install**:
   - Run installer
   - Add to PATH

3. **Install kubectl**:

```powershell
# Download kubectl
curl.exe -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"

# Move to Program Files
Move-Item .\kubectl.exe 'C:\Program Files\kubectl\kubectl.exe'

# Add to PATH
$kubectlPath = "C:\Program Files\kubectl"
$currentPath = [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::Machine)
[System.Environment]::SetEnvironmentVariable('Path', "$currentPath;$kubectlPath", [System.EnvironmentVariableTarget]::Machine)
```

4. **Start minikube**:

```bash
# Start minikube (uses Docker driver)
minikube start --driver=docker

# Verify
minikube status
# Expected: host: Running, kubelet: Running

kubectl version --client
# Expected: Client Version: v1.28.x

kubectl get nodes
# Expected: minikube   Ready    control-plane   1m    v1.28.x
```

### Verify Kubernetes

```bash
# Check cluster info
kubectl cluster-info

# Create test deployment
kubectl create deployment hello-minikube --image=k8s.gcr.io/echoserver:1.4

# Check pods
kubectl get pods
```

---

## ✅ Task 005: Set up Python Virtual Environment

**Status**: Ready to execute

### Using Python venv (Recommended)

```bash
# Navigate to project directory
cd C:\Users\techh\PycharmProjects\neurolake

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Activate (Git Bash - your current terminal)
source .venv/Scripts/activate

# Verify activation (should show (.venv) in prompt)
which python
# Expected: C:/Users/techh/PycharmProjects/neurolake/.venv/Scripts/python

# Verify Python version in venv
python --version
# Expected: Python 3.13.5
```

### Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install project dependencies
pip install -e ".[dev]"

# This will install from pyproject.toml:
# - pyspark>=3.5.0
# - delta-spark>=3.0.0
# - langchain>=0.3.0
# - fastapi>=0.115.0
# - And all other dependencies

# Verify key packages
pip show pyspark
pip show delta-spark
pip show langchain
```

### Create .env file

```bash
# Create environment configuration
cat > .env << 'EOF'
# NeuroLake Configuration

# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://neurolake:dev_password_change_in_prod@localhost:5432/neurolake

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (S3-compatible)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=neurolake
MINIO_SECRET_KEY=dev_password_change_in_prod
MINIO_BUCKET=neurolake-data

# Qdrant (Vector DB)
QDRANT_URL=http://localhost:6333

# LLM Configuration (add your keys)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Spark Configuration
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=8g
SPARK_EXECUTOR_CORES=4

# Logging
LOG_LEVEL=INFO
EOF

echo ".env file created! Update with your API keys."
```

### Verify Virtual Environment

```bash
# Check installed packages
pip list

# Should see:
# pyspark        3.5.x
# delta-spark    3.0.x
# langchain      0.3.x
# fastapi        0.115.x
# pandas         2.x
# And many more...

# Check Python paths
python -c "import sys; print('\n'.join(sys.path))"

# Should show .venv paths first
```

---

## 📋 Installation Checklist

After completing all tasks, verify:

```bash
# Task 001: Python
python --version
# ✓ Python 3.13.5

# Task 002: Java
java -version
# ✓ openjdk version "17.0.x"

echo $JAVA_HOME
# ✓ C:\Program Files\Eclipse Adoptium\jdk-17.x

# Task 003: Docker
docker --version
# ✓ Docker version 24.0.x

docker ps
# ✓ No errors (may be empty list)

# Task 004: Kubernetes
minikube status
# ✓ host: Running

kubectl version --client
# ✓ Client Version: v1.28.x

# Task 005: Python venv
which python
# ✓ Shows .venv path

pip show pyspark
# ✓ Version: 3.5.x
```

---

## 🔧 Common Issues & Solutions

### Issue 1: Java not in PATH

```powershell
# Fix in PowerShell (Administrator)
$javaHome = "C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot"
[System.Environment]::SetEnvironmentVariable('JAVA_HOME', $javaHome, 'Machine')
[System.Environment]::SetEnvironmentVariable('Path', "$env:Path;$javaHome\bin", 'Machine')

# Restart terminal
```

### Issue 2: Docker not starting

```powershell
# Check WSL 2
wsl --list --verbose
# Should show version 2

# If version 1, upgrade:
wsl --set-version Ubuntu 2

# Restart Docker Desktop
```

### Issue 3: minikube won't start

```bash
# Delete and recreate
minikube delete
minikube start --driver=docker --memory=8192 --cpus=4

# If still failing, check Docker is running:
docker ps
```

### Issue 4: Virtual environment not activating

```bash
# Windows PowerShell might block scripts
# Run in PowerShell as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again:
.\.venv\Scripts\Activate.ps1
```

### Issue 5: pip install fails

```bash
# Clear pip cache
pip cache purge

# Upgrade pip
python -m pip install --upgrade pip

# Try install again
pip install -e ".[dev]"

# If specific package fails, install manually:
pip install pyspark==3.5.0
pip install delta-spark==3.0.0
```

---

## 🎯 Next Steps After Setup

Once all 5 tasks are complete:

```bash
# 1. Verify all services
docker-compose up -d

# 2. Check services are running
docker ps
# Should see: postgres, redis, minio, qdrant, temporal

# 3. Test Python can import key packages
python -c "import pyspark; print(pyspark.__version__)"
python -c "import delta; print('Delta Lake OK')"
python -c "import langchain; print('LangChain OK')"

# 4. Create first Spark session
python << EOF
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("NeuroLake-Test") \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:3.0.0") \
    .getOrCreate()

print(f"Spark version: {spark.version}")
print("Spark session created successfully!")

spark.stop()
EOF

# 5. Move to Task 006!
```

---

## 📝 System Information

```bash
# Document your setup
cat > SYSTEM_INFO.md << 'EOF'
# NeuroLake Development Environment

**Date**: October 2024
**OS**: Windows 11
**Python**: 3.13.5
**Java**: OpenJDK 17.x
**Docker**: 24.0.x
**Kubernetes**: minikube v1.x
**IDE**: VS Code

## Installed Packages
See `pip list` output in .venv

## Environment Variables
- JAVA_HOME: Set
- PATH: Updated with Java, kubectl
- Virtual env: .venv activated

## Services Running
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO: localhost:9000
- Qdrant: localhost:6333
- Temporal: localhost:7233

## Next: Task 006
EOF

echo "Setup complete! Documentation saved to SYSTEM_INFO.md"
```

---

## 🆘 Need Help?

If you encounter issues:

1. **Check logs**:
   - Docker: Docker Desktop → Troubleshoot → Get Logs
   - minikube: `minikube logs`
   - Python: Check error messages

2. **Restart services**:
   ```bash
   docker-compose down
   docker-compose up -d
   minikube stop
   minikube start
   ```

3. **Verify versions match requirements**:
   - Python ≥ 3.11 ✓
   - Java ≥ 11
   - Docker ≥ 20.10
   - kubectl ≥ 1.25

4. **Google the error** or check:
   - Docker docs: https://docs.docker.com/
   - minikube docs: https://minikube.sigs.k8s.io/
   - PySpark docs: https://spark.apache.org/docs/latest/

---

**Ready to proceed? Let me know when you've completed Tasks 002-005, and we'll move to Task 006!**
