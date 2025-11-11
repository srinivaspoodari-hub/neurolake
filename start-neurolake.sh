#!/bin/bash

################################################################################
# NeuroLake Unified Startup Script
#
# This script handles the complete deployment of NeuroLake platform:
# - Backend (FastAPI)
# - Frontend (React)
# - Database (PostgreSQL)
# - Cache (Redis)
# - Storage (MinIO - optional)
#
# Usage:
#   ./start-neurolake.sh              # Start all services
#   ./start-neurolake.sh --stop       # Stop all services
#   ./start-neurolake.sh --restart    # Restart all services
#   ./start-neurolake.sh --status     # Check status
#   ./start-neurolake.sh --logs       # View logs
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/.pids"

# Service PIDs
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379
MINIO_PORT=9000

# Environment file
ENV_FILE="$SCRIPT_DIR/.env"

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_directories() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    mkdir -p "$SCRIPT_DIR/data"
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

wait_for_port() {
    local port=$1
    local service=$2
    local max_wait=30
    local count=0

    log_info "Waiting for $service on port $port..."
    while ! check_port $port; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $max_wait ]; then
            log_error "$service failed to start on port $port"
            return 1
        fi
    done
    log_success "$service is running on port $port"
    return 0
}

check_command() {
    local cmd=$1
    if ! command -v $cmd &> /dev/null; then
        log_error "$cmd is not installed"
        return 1
    fi
    return 0
}

################################################################################
# Prerequisites Check
################################################################################

check_prerequisites() {
    log_info "Checking prerequisites..."

    local all_ok=true

    # Check Python
    if check_command python3; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        log_success "Python $python_version found"
    else
        log_error "Python 3.11+ is required"
        all_ok=false
    fi

    # Check Node.js
    if check_command node; then
        local node_version=$(node --version)
        log_success "Node.js $node_version found"
    else
        log_error "Node.js 18+ is required"
        all_ok=false
    fi

    # Check PostgreSQL
    if check_command psql; then
        local pg_version=$(psql --version | cut -d' ' -f3)
        log_success "PostgreSQL $pg_version found"
    else
        log_warning "PostgreSQL not found (required for production)"
    fi

    # Check Redis
    if check_command redis-cli; then
        log_success "Redis CLI found"
    else
        log_warning "Redis not found (required for caching)"
    fi

    if [ "$all_ok" = false ]; then
        log_error "Prerequisites check failed. Please install missing dependencies."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

################################################################################
# Environment Setup
################################################################################

setup_environment() {
    log_info "Setting up environment..."

    # Create .env if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found, creating from template..."
        cat > "$ENV_FILE" << EOF
# Database
DATABASE_URL=postgresql://neurolake:neurolake@localhost:5432/neurolake

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Settings
API_SECRET_KEY=$(openssl rand -hex 32)
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
EOF
        log_success "Created .env file with default values"
        log_warning "Please configure Google API and Groq LLM keys in .env for full functionality"
    fi

    # Export environment variables
    set -a
    source "$ENV_FILE"
    set +a

    log_success "Environment loaded"
}

################################################################################
# Database Setup
################################################################################

setup_database() {
    log_info "Setting up database..."

    # Check if PostgreSQL is running
    if ! pg_isready -h localhost -p $POSTGRES_PORT > /dev/null 2>&1; then
        log_error "PostgreSQL is not running on port $POSTGRES_PORT"
        log_info "Please start PostgreSQL:"
        log_info "  sudo systemctl start postgresql"
        log_info "  OR"
        log_info "  docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=neurolake postgres:15"
        exit 1
    fi

    # Create database if it doesn't exist
    if ! psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw neurolake; then
        log_info "Creating neurolake database..."
        createdb -h localhost -U postgres neurolake || {
            log_warning "Failed to create database as postgres user, trying with current user..."
            createdb neurolake || {
                log_error "Failed to create database. Please create manually:"
                log_info "  createdb neurolake"
                exit 1
            }
        }
        log_success "Database created"
    else
        log_success "Database exists"
    fi

    # Run migrations
    if [ -d "$SCRIPT_DIR/neurolake/db/migrations" ]; then
        log_info "Running database migrations..."
        cd "$SCRIPT_DIR"
        python3 -m neurolake.db.migrations.run >> "$LOG_DIR/migrations.log" 2>&1 || {
            log_warning "Migrations failed or not implemented yet"
        }
    fi

    log_success "Database setup complete"
}

################################################################################
# Redis Setup
################################################################################

setup_redis() {
    log_info "Setting up Redis..."

    # Check if Redis is running
    if ! redis-cli ping > /dev/null 2>&1; then
        log_warning "Redis is not running"
        log_info "Attempting to start Redis..."

        # Try to start Redis
        redis-server --daemonize yes --port $REDIS_PORT >> "$LOG_DIR/redis.log" 2>&1 || {
            log_error "Failed to start Redis. Please start manually:"
            log_info "  redis-server"
            log_info "  OR"
            log_info "  docker run -d -p 6379:6379 redis:7"
            exit 1
        }

        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            log_success "Redis started successfully"
        else
            log_error "Redis failed to start"
            exit 1
        fi
    else
        log_success "Redis is running"
    fi
}

################################################################################
# Backend Setup & Start
################################################################################

setup_backend() {
    log_info "Setting up backend..."

    cd "$SCRIPT_DIR"

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install/upgrade dependencies
    log_info "Installing backend dependencies..."
    pip install --upgrade pip >> "$LOG_DIR/pip.log" 2>&1

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt >> "$LOG_DIR/pip.log" 2>&1
        log_success "Backend dependencies installed"
    else
        log_warning "requirements.txt not found, skipping dependency installation"
    fi

    log_success "Backend setup complete"
}

start_backend() {
    log_info "Starting backend..."

    # Check if backend is already running
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 $(cat "$BACKEND_PID_FILE") 2>/dev/null; then
        log_warning "Backend is already running (PID: $(cat $BACKEND_PID_FILE))"
        return 0
    fi

    # Kill any process on backend port
    if check_port $BACKEND_PORT; then
        log_warning "Port $BACKEND_PORT is in use, killing process..."
        kill $(lsof -t -i:$BACKEND_PORT) 2>/dev/null || true
        sleep 2
    fi

    cd "$SCRIPT_DIR"
    source venv/bin/activate

    # Start backend
    log_info "Starting FastAPI server on port $BACKEND_PORT..."
    nohup uvicorn neurolake.api.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        --log-level info \
        > "$LOG_DIR/backend.log" 2>&1 &

    local backend_pid=$!
    echo $backend_pid > "$BACKEND_PID_FILE"

    # Wait for backend to start
    if wait_for_port $BACKEND_PORT "Backend"; then
        log_success "Backend started (PID: $backend_pid)"
        log_info "Backend URL: http://localhost:$BACKEND_PORT"
        log_info "API Docs: http://localhost:$BACKEND_PORT/docs"
        return 0
    else
        log_error "Backend failed to start. Check logs: $LOG_DIR/backend.log"
        return 1
    fi
}

################################################################################
# Frontend Setup & Start
################################################################################

setup_frontend() {
    log_info "Setting up frontend..."

    cd "$SCRIPT_DIR/frontend"

    # Install dependencies
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies (this may take a few minutes)..."
        npm install >> "$LOG_DIR/npm.log" 2>&1
        log_success "Frontend dependencies installed"
    else
        log_success "Frontend dependencies already installed"
    fi

    # Create .env.local for frontend
    if [ ! -f ".env.local" ]; then
        log_info "Creating frontend environment file..."
        cat > .env.local << EOF
VITE_API_URL=http://localhost:$BACKEND_PORT
VITE_APP_TITLE=NeuroLake Data Platform
EOF
        log_success "Frontend environment file created"
    fi

    log_success "Frontend setup complete"
}

start_frontend() {
    log_info "Starting frontend..."

    # Check if frontend is already running
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        log_warning "Frontend is already running (PID: $(cat $FRONTEND_PID_FILE))"
        return 0
    fi

    # Kill any process on frontend port
    if check_port $FRONTEND_PORT; then
        log_warning "Port $FRONTEND_PORT is in use, killing process..."
        kill $(lsof -t -i:$FRONTEND_PORT) 2>/dev/null || true
        sleep 2
    fi

    cd "$SCRIPT_DIR/frontend"

    # Start frontend
    log_info "Starting React dev server on port $FRONTEND_PORT..."
    nohup npm run dev -- --port $FRONTEND_PORT --host 0.0.0.0 \
        > "$LOG_DIR/frontend.log" 2>&1 &

    local frontend_pid=$!
    echo $frontend_pid > "$FRONTEND_PID_FILE"

    # Wait for frontend to start
    if wait_for_port $FRONTEND_PORT "Frontend"; then
        log_success "Frontend started (PID: $frontend_pid)"
        log_info "Frontend URL: http://localhost:$FRONTEND_PORT"
        return 0
    else
        log_error "Frontend failed to start. Check logs: $LOG_DIR/frontend.log"
        return 1
    fi
}

################################################################################
# Stop Services
################################################################################

stop_services() {
    log_info "Stopping services..."

    # Stop backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE")
        if kill -0 $backend_pid 2>/dev/null; then
            log_info "Stopping backend (PID: $backend_pid)..."
            kill $backend_pid
            rm "$BACKEND_PID_FILE"
            log_success "Backend stopped"
        else
            log_warning "Backend process not found"
            rm "$BACKEND_PID_FILE"
        fi
    fi

    # Stop frontend
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        if kill -0 $frontend_pid 2>/dev/null; then
            log_info "Stopping frontend (PID: $frontend_pid)..."
            kill $frontend_pid
            rm "$FRONTEND_PID_FILE"
            log_success "Frontend stopped"
        else
            log_warning "Frontend process not found"
            rm "$FRONTEND_PID_FILE"
        fi
    fi

    # Kill any remaining processes on ports
    if check_port $BACKEND_PORT; then
        log_warning "Killing remaining process on port $BACKEND_PORT..."
        kill $(lsof -t -i:$BACKEND_PORT) 2>/dev/null || true
    fi

    if check_port $FRONTEND_PORT; then
        log_warning "Killing remaining process on port $FRONTEND_PORT..."
        kill $(lsof -t -i:$FRONTEND_PORT) 2>/dev/null || true
    fi

    log_success "All services stopped"
}

################################################################################
# Status Check
################################################################################

check_status() {
    log_info "Checking service status..."
    echo ""

    # Backend status
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 $(cat "$BACKEND_PID_FILE") 2>/dev/null; then
        log_success "Backend: RUNNING (PID: $(cat $BACKEND_PID_FILE))"
        log_info "  URL: http://localhost:$BACKEND_PORT"
    else
        log_error "Backend: STOPPED"
    fi

    # Frontend status
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        log_success "Frontend: RUNNING (PID: $(cat $FRONTEND_PID_FILE))"
        log_info "  URL: http://localhost:$FRONTEND_PORT"
    else
        log_error "Frontend: STOPPED"
    fi

    # PostgreSQL status
    if pg_isready -h localhost -p $POSTGRES_PORT > /dev/null 2>&1; then
        log_success "PostgreSQL: RUNNING"
    else
        log_error "PostgreSQL: STOPPED"
    fi

    # Redis status
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: RUNNING"
    else
        log_error "Redis: STOPPED"
    fi

    echo ""
}

################################################################################
# View Logs
################################################################################

view_logs() {
    log_info "Viewing logs (Ctrl+C to exit)..."
    echo ""

    if [ -f "$LOG_DIR/backend.log" ] && [ -f "$LOG_DIR/frontend.log" ]; then
        tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
    elif [ -f "$LOG_DIR/backend.log" ]; then
        tail -f "$LOG_DIR/backend.log"
    elif [ -f "$LOG_DIR/frontend.log" ]; then
        tail -f "$LOG_DIR/frontend.log"
    else
        log_warning "No logs found"
    fi
}

################################################################################
# Health Check
################################################################################

health_check() {
    log_info "Running health checks..."

    local all_healthy=true

    # Backend health
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        all_healthy=false
    fi

    # Frontend health (just check if port responds)
    if check_port $FRONTEND_PORT; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        all_healthy=false
    fi

    # Database health
    if psql -h localhost -d neurolake -c "SELECT 1" > /dev/null 2>&1; then
        log_success "Database health check passed"
    else
        log_error "Database health check failed"
        all_healthy=false
    fi

    # Redis health
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis health check passed"
    else
        log_error "Redis health check failed"
        all_healthy=false
    fi

    if [ "$all_healthy" = true ]; then
        log_success "All health checks passed ✅"
        return 0
    else
        log_error "Some health checks failed ❌"
        return 1
    fi
}

################################################################################
# Main
################################################################################

main() {
    clear
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              NeuroLake Platform Launcher                  ║"
    echo "║          AI-Native Data Platform - Version 1.0             ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    create_directories

    case "${1:-start}" in
        start)
            check_prerequisites
            setup_environment
            setup_database
            setup_redis
            setup_backend
            start_backend
            setup_frontend
            start_frontend
            echo ""
            echo "╔════════════════════════════════════════════════════════════╗"
            echo "║                    Startup Complete!                       ║"
            echo "╠════════════════════════════════════════════════════════════╣"
            echo "║  Backend:  http://localhost:$BACKEND_PORT                         ║"
            echo "║  Frontend: http://localhost:$FRONTEND_PORT                         ║"
            echo "║  API Docs: http://localhost:$BACKEND_PORT/docs                ║"
            echo "╠════════════════════════════════════════════════════════════╣"
            echo "║  Logs:     $LOG_DIR/                    ║"
            echo "║  PIDs:     $PID_DIR/                     ║"
            echo "╠════════════════════════════════════════════════════════════╣"
            echo "║  Commands:                                                 ║"
            echo "║    ./start-neurolake.sh --status    Check status          ║"
            echo "║    ./start-neurolake.sh --logs      View logs             ║"
            echo "║    ./start-neurolake.sh --stop      Stop services         ║"
            echo "║    ./start-neurolake.sh --restart   Restart services      ║"
            echo "╚════════════════════════════════════════════════════════════╝"
            echo ""
            health_check
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            $0 start
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        health)
            health_check
            ;;
        *)
            log_error "Unknown command: $1"
            echo "Usage: $0 {start|stop|restart|status|logs|health}"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
