# NeuroLake API Dockerfile
# Multi-stage build for optimal image size and security

# Stage 1: Builder stage
FROM python:3.11-slim-bookworm AS builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.0

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
WORKDIR /build
COPY pyproject.toml README.md ./
COPY requirements.txt requirements-dev.txt* ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy source code
COPY neurolake/ ./neurolake/
COPY setup_cython.py* ./

# Build and install the package
RUN pip install -e .


# Stage 2: Rust builder (for NCF Rust components)
FROM rust:1.75-slim-bookworm AS rust-builder

WORKDIR /build

# Install dependencies for Rust
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust workspace
COPY Cargo.toml* ./
COPY core/ ./core/

# Build Rust components in release mode
RUN cd core/ncf-rust && cargo build --release || true


# Stage 3: Final runtime image
FROM python:3.11-slim-bookworm

# Set labels for image metadata
LABEL maintainer="NeuroLake Team <team@neurolake.dev>" \
      description="NeuroLake AI-Native Data Platform API" \
      version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    # API Configuration
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    API_WORKERS=4 \
    API_RELOAD=false \
    # Application
    ENV=production \
    LOG_LEVEL=info \
    # Security
    ALLOWED_HOSTS="*" \
    CORS_ORIGINS="*"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r neurolake --gid=999 && \
    useradd -r -g neurolake --uid=999 --home-dir=/app --shell=/bin/bash neurolake

# Create necessary directories
RUN mkdir -p /app /data /logs /cache && \
    chown -R neurolake:neurolake /app /data /logs /cache

# Copy virtual environment from builder
COPY --from=builder --chown=neurolake:neurolake /opt/venv /opt/venv

# Copy Rust binaries if they exist
COPY --from=rust-builder --chown=neurolake:neurolake /build/core/ncf-rust/target/release/libncf* /usr/local/lib/ || true

# Copy application code
WORKDIR /app
COPY --chown=neurolake:neurolake neurolake/ ./neurolake/
COPY --chown=neurolake:neurolake pyproject.toml README.md ./

# Copy additional configuration files
COPY --chown=neurolake:neurolake .env.example ./.env.example

# Health check script
COPY --chown=neurolake:neurolake <<'EOF' /app/healthcheck.py
#!/usr/bin/env python3
import sys
import httpx

def check_health():
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code == 200:
            sys.exit(0)
        sys.exit(1)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    check_health()
EOF

RUN chmod +x /app/healthcheck.py

# Switch to non-root user
USER neurolake

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Volume mounts for persistent data
VOLUME ["/data", "/logs", "/cache"]

# Default command: Start FastAPI with Uvicorn
CMD ["uvicorn", "neurolake.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
