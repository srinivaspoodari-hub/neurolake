# NeuroLake Docker Deployment Guide

This guide explains how to build and deploy NeuroLake using Docker and Docker Compose.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

## Quick Start

### 1. Build the Docker Image

```bash
# Build the API image
docker build -t neurolake/api:latest .

# Or build with specific platform
docker build --platform linux/amd64 -t neurolake/api:latest .
```

### 2. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

### 3. Access Services

- **NeuroLake API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **Grafana**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Temporal UI**: http://localhost:8080

## Docker Image Details

### Multi-Stage Build

The Dockerfile uses a multi-stage build approach:

1. **Builder Stage**: Installs Python dependencies and builds the package
2. **Rust Builder Stage**: Compiles NCF Rust components (optional)
3. **Runtime Stage**: Creates minimal production image

### Image Optimizations

- Base image: `python:3.11-slim-bookworm`
- Non-root user (uid: 999)
- Virtual environment for dependency isolation
- Health check included
- Multi-platform support (amd64, arm64)

### Image Size

- Approximate size: 1.5-2GB (with all dependencies)
- Compressed size: 600-800MB

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Copy example
cp .env.example .env

# Edit configuration
nano .env
```

Key environment variables:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/neurolake

# Redis
REDIS_URL=redis://redis:6379/0

# S3/MinIO
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=neurolake
S3_SECRET_KEY=change_me
S3_BUCKET=neurolake-data

# Qdrant
QDRANT_URL=http://qdrant:6333

# Environment
ENV=production
LOG_LEVEL=info
```

### Volume Mounts

The API container uses the following volumes:

- `/data` - Persistent data storage
- `/logs` - Application logs
- `/cache` - Cache directory

## Production Deployment

### 1. Security Best Practices

```bash
# Use secrets for sensitive data
docker secret create postgres_password postgres_password.txt
docker secret create s3_secret_key s3_secret.txt

# Update docker-compose.yml to use secrets
```

### 2. Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

### 3. Production Configuration

```bash
# Use production environment
export ENV=production

# Disable API reload
export API_RELOAD=false

# Set worker count based on CPU cores
export API_WORKERS=4

# Enable HTTPS
export API_TLS_CERT=/certs/cert.pem
export API_TLS_KEY=/certs/key.pem
```

### 4. Build for Multiple Platforms

```bash
# Create buildx builder
docker buildx create --name neurolake-builder --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t neurolake/api:latest \
  --push \
  .
```

## Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' neurolake-api

# Manual health check
curl http://localhost:8000/health
```

Health check endpoint returns:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "storage": "connected"
  }
}
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### Logs

View real-time logs:

```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Distributed Tracing

Access Jaeger UI at http://localhost:16686 to view distributed traces.

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Inspect container
docker inspect neurolake-api

# Check resource usage
docker stats neurolake-api
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U neurolake -d neurolake
```

### Performance Issues

```bash
# Increase worker count
export API_WORKERS=8

# Allocate more memory
docker-compose up -d --scale api=2
```

## Development

### Hot Reload for Development

For local development with hot reload:

```yaml
api:
  build:
    context: .
    target: builder  # Use builder stage
  volumes:
    - ./neurolake:/app/neurolake  # Mount source code
  environment:
    - API_RELOAD=true
  command: ["uvicorn", "neurolake.api.main:app", "--reload", "--host", "0.0.0.0"]
```

### Running Tests in Docker

```bash
# Run tests
docker-compose exec api pytest

# Run specific test
docker-compose exec api pytest tests/test_api.py

# With coverage
docker-compose exec api pytest --cov=neurolake
```

## Maintenance

### Backup Data

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U neurolake neurolake > backup.sql

# Backup volumes
docker run --rm -v neurolake_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data
```

### Update Image

```bash
# Pull latest changes
git pull origin main

# Rebuild image
docker-compose build --no-cache api

# Restart with new image
docker-compose up -d api
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker rmi neurolake/api:latest

# Prune unused resources
docker system prune -a
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: neurolake/api:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/neurolake/neurolake/issues
- Documentation: https://docs.neurolake.dev
- Email: team@neurolake.dev
