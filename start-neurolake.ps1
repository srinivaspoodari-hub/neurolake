################################################################################
# NeuroLake Unified Startup Script for Windows
#
# This script handles the complete deployment of NeuroLake platform:
# - Backend (FastAPI)
# - Frontend (React)
# - Database (PostgreSQL)
# - Cache (Redis)
#
# Usage:
#   .\start-neurolake.ps1              # Start all services
#   .\start-neurolake.ps1 -Stop        # Stop all services
#   .\start-neurolake.ps1 -Restart     # Restart all services
#   .\start-neurolake.ps1 -Status      # Check status
#   .\start-neurolake.ps1 -Logs        # View logs
#   .\start-neurolake.ps1 -Health      # Run health checks
################################################################################

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [switch]$Logs,
    [switch]$Health
)

# Configuration
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_DIR = Join-Path $SCRIPT_DIR "logs"
$PID_DIR = Join-Path $SCRIPT_DIR ".pids"

# Service PIDs
$BACKEND_PID_FILE = Join-Path $PID_DIR "backend.pid"
$FRONTEND_PID_FILE = Join-Path $PID_DIR "frontend.pid"

# Ports
$BACKEND_PORT = 8000
$FRONTEND_PORT = 3000
$POSTGRES_PORT = 5432
$REDIS_PORT = 6379

# Environment file
$ENV_FILE = Join-Path $SCRIPT_DIR ".env"

################################################################################
# Helper Functions
################################################################################

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Create-Directories {
    New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
    New-Item -ItemType Directory -Force -Path $PID_DIR | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $SCRIPT_DIR "data") | Out-Null
}

function Test-Port {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$ServiceName,
        [int]$MaxWait = 30
    )

    Write-Info "Waiting for $ServiceName on port $Port..."
    $count = 0

    while (-not (Test-Port -Port $Port)) {
        Start-Sleep -Seconds 1
        $count++
        if ($count -ge $MaxWait) {
            Write-Error "$ServiceName failed to start on port $Port"
            return $false
        }
    }

    Write-Success "$ServiceName is running on port $Port"
    return $true
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

################################################################################
# Prerequisites Check
################################################################################

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    $allOk = $true

    # Check Python
    if (Test-Command "python") {
        $pythonVersion = python --version
        Write-Success "$pythonVersion found"
    } else {
        Write-Error "Python 3.11+ is required"
        $allOk = $false
    }

    # Check Node.js
    if (Test-Command "node") {
        $nodeVersion = node --version
        Write-Success "Node.js $nodeVersion found"
    } else {
        Write-Error "Node.js 18+ is required"
        $allOk = $false
    }

    # Check PostgreSQL
    if (Test-Command "psql") {
        $pgVersion = (psql --version).Split()[2]
        Write-Success "PostgreSQL $pgVersion found"
    } else {
        Write-Warning "PostgreSQL not found (required for production)"
    }

    # Check Redis
    if (Test-Command "redis-cli") {
        Write-Success "Redis CLI found"
    } else {
        Write-Warning "Redis not found (required for caching)"
    }

    if (-not $allOk) {
        Write-Error "Prerequisites check failed. Please install missing dependencies."
        exit 1
    }

    Write-Success "Prerequisites check passed"
}

################################################################################
# Environment Setup
################################################################################

function Initialize-Environment {
    Write-Info "Setting up environment..."

    # Create .env if it doesn't exist
    if (-not (Test-Path $ENV_FILE)) {
        Write-Warning ".env file not found, creating from template..."

        # Generate random API key
        $apiKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

        @"
# Database
DATABASE_URL=postgresql://neurolake:neurolake@localhost:5432/neurolake

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Settings
API_SECRET_KEY=$apiKey
API_ENVIRONMENT=development
API_DEBUG=true
API_PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Storage
STORAGE_BACKEND=local
STORAGE_PATH=$SCRIPT_DIR/data/storage

# Google API (Optional - configure if needed)
#GOOGLE_CLIENT_ID=your-client-id
#GOOGLE_CLIENT_SECRET=your-client-secret

# Groq LLM (Optional - configure if needed)
#GROQ_API_KEY=your-groq-api-key

# Spark
SPARK_MASTER=local[*]
PHOTON_ENABLED=false
"@ | Out-File -FilePath $ENV_FILE -Encoding utf8

        Write-Success "Created .env file with default values"
        Write-Warning "Please configure Google API and Groq LLM keys in .env for full functionality"
    }

    # Load environment variables
    Get-Content $ENV_FILE | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }

    Write-Success "Environment loaded"
}

################################################################################
# Database Setup
################################################################################

function Initialize-Database {
    Write-Info "Setting up database..."

    # Check if PostgreSQL is running
    try {
        $pgReady = & pg_isready -h localhost -p $POSTGRES_PORT 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "PostgreSQL not ready"
        }
    } catch {
        Write-Error "PostgreSQL is not running on port $POSTGRES_PORT"
        Write-Info "Please start PostgreSQL:"
        Write-Info "  Option 1: Start PostgreSQL service"
        Write-Info "  Option 2: Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=neurolake postgres:15"
        exit 1
    }

    # Create database if it doesn't exist
    $dbExists = & psql -h localhost -U postgres -lqt 2>&1 | Select-String "neurolake"
    if (-not $dbExists) {
        Write-Info "Creating neurolake database..."
        & createdb -h localhost -U postgres neurolake 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database created"
        } else {
            Write-Warning "Failed to create database. Please create manually: createdb neurolake"
        }
    } else {
        Write-Success "Database exists"
    }

    Write-Success "Database setup complete"
}

################################################################################
# Redis Setup
################################################################################

function Initialize-Redis {
    Write-Info "Setting up Redis..."

    # Check if Redis is running
    try {
        $redisPing = & redis-cli ping 2>&1
        if ($redisPing -eq "PONG") {
            Write-Success "Redis is running"
        } else {
            throw "Redis not responding"
        }
    } catch {
        Write-Warning "Redis is not running"
        Write-Info "Please start Redis:"
        Write-Info "  Option 1: Start Redis service"
        Write-Info "  Option 2: Docker: docker run -d -p 6379:6379 redis:7"
        exit 1
    }
}

################################################################################
# Backend Setup & Start
################################################################################

function Initialize-Backend {
    Write-Info "Setting up backend..."

    Set-Location $SCRIPT_DIR

    # Check if virtual environment exists
    if (-not (Test-Path "venv")) {
        Write-Info "Creating Python virtual environment..."
        python -m venv venv
        Write-Success "Virtual environment created"
    }

    # Activate virtual environment
    $venvActivate = Join-Path $SCRIPT_DIR "venv\Scripts\Activate.ps1"
    & $venvActivate

    # Install/upgrade dependencies
    Write-Info "Installing backend dependencies..."
    python -m pip install --upgrade pip > "$LOG_DIR\pip.log" 2>&1

    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt >> "$LOG_DIR\pip.log" 2>&1
        Write-Success "Backend dependencies installed"
    } else {
        Write-Warning "requirements.txt not found, skipping dependency installation"
    }

    Write-Success "Backend setup complete"
}

function Start-Backend {
    Write-Info "Starting backend..."

    # Check if backend is already running
    if ((Test-Path $BACKEND_PID_FILE)) {
        $pid = Get-Content $BACKEND_PID_FILE
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Warning "Backend is already running (PID: $pid)"
            return
        }
    }

    # Kill any process on backend port
    if (Test-Port -Port $BACKEND_PORT) {
        Write-Warning "Port $BACKEND_PORT is in use, killing process..."
        $process = Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
        if ($process) {
            Stop-Process -Id $process -Force
            Start-Sleep -Seconds 2
        }
    }

    Set-Location $SCRIPT_DIR

    # Activate venv
    $venvActivate = Join-Path $SCRIPT_DIR "venv\Scripts\Activate.ps1"
    & $venvActivate

    # Start backend
    Write-Info "Starting FastAPI server on port $BACKEND_PORT..."
    $backendJob = Start-Process -FilePath "uvicorn" -ArgumentList "neurolake.api.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload --log-level info" -PassThru -RedirectStandardOutput "$LOG_DIR\backend.log" -RedirectStandardError "$LOG_DIR\backend_error.log" -WindowStyle Hidden

    $backendJob.Id | Out-File -FilePath $BACKEND_PID_FILE

    # Wait for backend to start
    if (Wait-ForPort -Port $BACKEND_PORT -ServiceName "Backend") {
        Write-Success "Backend started (PID: $($backendJob.Id))"
        Write-Info "Backend URL: http://localhost:$BACKEND_PORT"
        Write-Info "API Docs: http://localhost:$BACKEND_PORT/docs"
    } else {
        Write-Error "Backend failed to start. Check logs: $LOG_DIR\backend.log"
    }
}

################################################################################
# Frontend Setup & Start
################################################################################

function Initialize-Frontend {
    Write-Info "Setting up frontend..."

    Set-Location (Join-Path $SCRIPT_DIR "frontend")

    # Install dependencies
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing frontend dependencies (this may take a few minutes)..."
        npm install >> "$LOG_DIR\npm.log" 2>&1
        Write-Success "Frontend dependencies installed"
    } else {
        Write-Success "Frontend dependencies already installed"
    }

    # Create .env.local for frontend
    if (-not (Test-Path ".env.local")) {
        Write-Info "Creating frontend environment file..."
        @"
VITE_API_URL=http://localhost:$BACKEND_PORT
VITE_APP_TITLE=NeuroLake Data Platform
"@ | Out-File -FilePath ".env.local" -Encoding utf8
        Write-Success "Frontend environment file created"
    }

    Write-Success "Frontend setup complete"
}

function Start-Frontend {
    Write-Info "Starting frontend..."

    # Check if frontend is already running
    if ((Test-Path $FRONTEND_PID_FILE)) {
        $pid = Get-Content $FRONTEND_PID_FILE
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Warning "Frontend is already running (PID: $pid)"
            return
        }
    }

    # Kill any process on frontend port
    if (Test-Port -Port $FRONTEND_PORT) {
        Write-Warning "Port $FRONTEND_PORT is in use, killing process..."
        $process = Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
        if ($process) {
            Stop-Process -Id $process -Force
            Start-Sleep -Seconds 2
        }
    }

    Set-Location (Join-Path $SCRIPT_DIR "frontend")

    # Start frontend
    Write-Info "Starting React dev server on port $FRONTEND_PORT..."
    $frontendJob = Start-Process -FilePath "npm" -ArgumentList "run dev -- --port $FRONTEND_PORT --host 0.0.0.0" -PassThru -RedirectStandardOutput "$LOG_DIR\frontend.log" -RedirectStandardError "$LOG_DIR\frontend_error.log" -WindowStyle Hidden

    $frontendJob.Id | Out-File -FilePath $FRONTEND_PID_FILE

    # Wait for frontend to start
    if (Wait-ForPort -Port $FRONTEND_PORT -ServiceName "Frontend") {
        Write-Success "Frontend started (PID: $($frontendJob.Id))"
        Write-Info "Frontend URL: http://localhost:$FRONTEND_PORT"
    } else {
        Write-Error "Frontend failed to start. Check logs: $LOG_DIR\frontend.log"
    }
}

################################################################################
# Stop Services
################################################################################

function Stop-Services {
    Write-Info "Stopping services..."

    # Stop backend
    if (Test-Path $BACKEND_PID_FILE) {
        $backendPid = Get-Content $BACKEND_PID_FILE
        if (Get-Process -Id $backendPid -ErrorAction SilentlyContinue) {
            Write-Info "Stopping backend (PID: $backendPid)..."
            Stop-Process -Id $backendPid -Force
            Remove-Item $BACKEND_PID_FILE
            Write-Success "Backend stopped"
        } else {
            Write-Warning "Backend process not found"
            Remove-Item $BACKEND_PID_FILE
        }
    }

    # Stop frontend
    if (Test-Path $FRONTEND_PID_FILE) {
        $frontendPid = Get-Content $FRONTEND_PID_FILE
        if (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue) {
            Write-Info "Stopping frontend (PID: $frontendPid)..."
            Stop-Process -Id $frontendPid -Force
            Remove-Item $FRONTEND_PID_FILE
            Write-Success "Frontend stopped"
        } else {
            Write-Warning "Frontend process not found"
            Remove-Item $FRONTEND_PID_FILE
        }
    }

    # Kill any remaining processes on ports
    if (Test-Port -Port $BACKEND_PORT) {
        Write-Warning "Killing remaining process on port $BACKEND_PORT..."
        $process = Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
        if ($process) {
            Stop-Process -Id $process -Force
        }
    }

    if (Test-Port -Port $FRONTEND_PORT) {
        Write-Warning "Killing remaining process on port $FRONTEND_PORT..."
        $process = Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
        if ($process) {
            Stop-Process -Id $process -Force
        }
    }

    Write-Success "All services stopped"
}

################################################################################
# Status Check
################################################################################

function Show-Status {
    Write-Info "Checking service status..."
    Write-Host ""

    # Backend status
    if ((Test-Path $BACKEND_PID_FILE)) {
        $pid = Get-Content $BACKEND_PID_FILE
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Success "Backend: RUNNING (PID: $pid)"
            Write-Info "  URL: http://localhost:$BACKEND_PORT"
        } else {
            Write-Error "Backend: STOPPED"
        }
    } else {
        Write-Error "Backend: STOPPED"
    }

    # Frontend status
    if ((Test-Path $FRONTEND_PID_FILE)) {
        $pid = Get-Content $FRONTEND_PID_FILE
        if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
            Write-Success "Frontend: RUNNING (PID: $pid)"
            Write-Info "  URL: http://localhost:$FRONTEND_PORT"
        } else {
            Write-Error "Frontend: STOPPED"
        }
    } else {
        Write-Error "Frontend: STOPPED"
    }

    # PostgreSQL status
    try {
        $null = & pg_isready -h localhost -p $POSTGRES_PORT 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "PostgreSQL: RUNNING"
        } else {
            Write-Error "PostgreSQL: STOPPED"
        }
    } catch {
        Write-Error "PostgreSQL: STOPPED"
    }

    # Redis status
    try {
        $redisPing = & redis-cli ping 2>&1
        if ($redisPing -eq "PONG") {
            Write-Success "Redis: RUNNING"
        } else {
            Write-Error "Redis: STOPPED"
        }
    } catch {
        Write-Error "Redis: STOPPED"
    }

    Write-Host ""
}

################################################################################
# View Logs
################################################################################

function Show-Logs {
    Write-Info "Viewing logs (Ctrl+C to exit)..."
    Write-Host ""

    $backendLog = Join-Path $LOG_DIR "backend.log"
    $frontendLog = Join-Path $LOG_DIR "frontend.log"

    if ((Test-Path $backendLog) -and (Test-Path $frontendLog)) {
        Get-Content $backendLog, $frontendLog -Wait
    } elseif (Test-Path $backendLog) {
        Get-Content $backendLog -Wait
    } elseif (Test-Path $frontendLog) {
        Get-Content $frontendLog -Wait
    } else {
        Write-Warning "No logs found"
    }
}

################################################################################
# Health Check
################################################################################

function Test-Health {
    Write-Info "Running health checks..."

    $allHealthy = $true

    # Backend health
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend health check passed"
        } else {
            Write-Error "Backend health check failed"
            $allHealthy = $false
        }
    } catch {
        Write-Error "Backend health check failed"
        $allHealthy = $false
    }

    # Frontend health
    if (Test-Port -Port $FRONTEND_PORT) {
        Write-Success "Frontend health check passed"
    } else {
        Write-Error "Frontend health check failed"
        $allHealthy = $false
    }

    # Database health
    try {
        $null = & psql -h localhost -d neurolake -c "SELECT 1" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Database health check passed"
        } else {
            Write-Error "Database health check failed"
            $allHealthy = $false
        }
    } catch {
        Write-Error "Database health check failed"
        $allHealthy = $false
    }

    # Redis health
    try {
        $redisPing = & redis-cli ping 2>&1
        if ($redisPing -eq "PONG") {
            Write-Success "Redis health check passed"
        } else {
            Write-Error "Redis health check failed"
            $allHealthy = $false
        }
    } catch {
        Write-Error "Redis health check failed"
        $allHealthy = $false
    }

    if ($allHealthy) {
        Write-Success "All health checks passed ✅"
        return $true
    } else {
        Write-Error "Some health checks failed ❌"
        return $false
    }
}

################################################################################
# Main
################################################################################

function Main {
    Clear-Host
    Write-Host "╔════════════════════════════════════════════════════════════╗"
    Write-Host "║              NeuroLake Platform Launcher                  ║"
    Write-Host "║          AI-Native Data Platform - Version 1.0             ║"
    Write-Host "╚════════════════════════════════════════════════════════════╝"
    Write-Host ""

    Create-Directories

    if ($Stop) {
        Stop-Services
    } elseif ($Restart) {
        Stop-Services
        Start-Sleep -Seconds 2
        & $MyInvocation.MyCommand.Path
    } elseif ($Status) {
        Show-Status
    } elseif ($Logs) {
        Show-Logs
    } elseif ($Health) {
        Test-Health
    } else {
        # Start all services
        Test-Prerequisites
        Initialize-Environment
        Initialize-Database
        Initialize-Redis
        Initialize-Backend
        Start-Backend
        Initialize-Frontend
        Start-Frontend

        Write-Host ""
        Write-Host "╔════════════════════════════════════════════════════════════╗"
        Write-Host "║                    Startup Complete!                       ║"
        Write-Host "╠════════════════════════════════════════════════════════════╣"
        Write-Host "║  Backend:  http://localhost:$BACKEND_PORT                         ║"
        Write-Host "║  Frontend: http://localhost:$FRONTEND_PORT                         ║"
        Write-Host "║  API Docs: http://localhost:$BACKEND_PORT/docs                ║"
        Write-Host "╠════════════════════════════════════════════════════════════╣"
        Write-Host "║  Logs:     $LOG_DIR                    ║"
        Write-Host "║  PIDs:     $PID_DIR                     ║"
        Write-Host "╠════════════════════════════════════════════════════════════╣"
        Write-Host "║  Commands:                                                 ║"
        Write-Host "║    .\start-neurolake.ps1 -Status    Check status          ║"
        Write-Host "║    .\start-neurolake.ps1 -Logs      View logs             ║"
        Write-Host "║    .\start-neurolake.ps1 -Stop      Stop services         ║"
        Write-Host "║    .\start-neurolake.ps1 -Restart   Restart services      ║"
        Write-Host "╚════════════════════════════════════════════════════════════╝"
        Write-Host ""

        Test-Health
    }
}

# Run main
Main
