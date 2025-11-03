# NeuroLake Configuration Guide

Complete reference for configuring NeuroLake using Pydantic Settings and environment variables.

## Quick Start

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

Load settings in Python:

```python
from neurolake.config import get_settings

settings = get_settings()
print(settings.database.connection_string)
```

## Configuration Overview

- All settings use `NEUROLAKE_` prefix
- Nested settings use `__` delimiter
- Example: `NEUROLAKE_DATABASE__HOST=localhost`
- Type-safe with Pydantic validation
- Default values for development

## Database Settings (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_DATABASE__HOST` | `localhost` | Database host |
| `NEUROLAKE_DATABASE__PORT` | `5432` | Database port (1-65535) |
| `NEUROLAKE_DATABASE__DATABASE` | `neurolake` | Database name |
| `NEUROLAKE_DATABASE__USERNAME` | `neurolake` | Database user |
| `NEUROLAKE_DATABASE__PASSWORD` | `dev_password_change_in_prod` | Database password |
| `NEUROLAKE_DATABASE__POOL_SIZE` | `20` | Connection pool size |
| `NEUROLAKE_DATABASE__SSLMODE` | `prefer` | SSL mode (disable, prefer, require) |

## Storage Settings (MinIO/S3)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_STORAGE__ENDPOINT` | `localhost:9000` | MinIO/S3 endpoint |
| `NEUROLAKE_STORAGE__ACCESS_KEY` | `neurolake` | Access key |
| `NEUROLAKE_STORAGE__SECRET_KEY` | `dev_password_change_in_prod` | Secret key |
| `NEUROLAKE_STORAGE__SECURE` | `false` | Use HTTPS |
| `NEUROLAKE_STORAGE__DATA_BUCKET` | `data` | Main data bucket |
| `NEUROLAKE_STORAGE__TEMP_BUCKET` | `temp` | Temporary bucket |

## Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_REDIS__HOST` | `localhost` | Redis host |
| `NEUROLAKE_REDIS__PORT` | `6379` | Redis port |
| `NEUROLAKE_REDIS__DB` | `0` | Database number (0-15) |
| `NEUROLAKE_REDIS__DEFAULT_TTL` | `3600` | Default cache TTL (seconds) |

## Qdrant Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_QDRANT__HOST` | `localhost` | Qdrant host |
| `NEUROLAKE_QDRANT__PORT` | `6333` | HTTP port |
| `NEUROLAKE_QDRANT__GRPC_PORT` | `6334` | gRPC port |
| `NEUROLAKE_QDRANT__VECTOR_SIZE` | `1536` | Vector dimensions |

## LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_LLM__DEFAULT_PROVIDER` | `openai` | Provider: openai or anthropic |
| `NEUROLAKE_LLM_OPENAI__API_KEY` | `None` | OpenAI API key |
| `NEUROLAKE_LLM_OPENAI__MODEL` | `gpt-4-turbo-preview` | OpenAI model |
| `NEUROLAKE_LLM_ANTHROPIC__API_KEY` | `None` | Anthropic API key |
| `NEUROLAKE_LLM_ANTHROPIC__MODEL` | `claude-3-5-sonnet-20241022` | Anthropic model |

## API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_API__HOST` | `0.0.0.0` | API host |
| `NEUROLAKE_API__PORT` | `8000` | API port |
| `NEUROLAKE_API__WORKERS` | `4` | Worker processes (1-32) |
| `NEUROLAKE_API__SECRET_KEY` | `dev_secret_key...` | JWT secret (change in prod) |
| `NEUROLAKE_API__RATE_LIMIT_REQUESTS` | `100` | Requests per window |

## Monitoring Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUROLAKE_MONITORING__ENABLE_METRICS` | `true` | Enable Prometheus metrics |
| `NEUROLAKE_MONITORING__METRICS_PORT` | `9090` | Metrics port |
| `NEUROLAKE_MONITORING__LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `NEUROLAKE_MONITORING__LOG_FORMAT` | `json` | Log format (json or text) |

## Production Checklist

Before deploying to production:

1. Set `NEUROLAKE_ENVIRONMENT=production`
2. Change all default passwords
3. Generate strong secret: `openssl rand -hex 32`
4. Enable SSL: `NEUROLAKE_DATABASE__SSLMODE=require`
5. Enable HTTPS: `NEUROLAKE_STORAGE__SECURE=true`
6. Configure proper CORS origins
7. Set up LLM API keys
8. Configure Redis password
9. Adjust rate limits for production
10. Enable monitoring

## Example Production Config

```bash
NEUROLAKE_ENVIRONMENT=production
NEUROLAKE_DEBUG=false
NEUROLAKE_DATABASE__PASSWORD=<strong-password>
NEUROLAKE_DATABASE__SSLMODE=require
NEUROLAKE_STORAGE__SECURE=true
NEUROLAKE_API__SECRET_KEY=<32-byte-hex>
NEUROLAKE_LLM_OPENAI__API_KEY=sk-...
```

## Docker Compose

When using Docker, services use different hostnames:

```bash
NEUROLAKE_DATABASE__HOST=postgres
NEUROLAKE_REDIS__HOST=redis
NEUROLAKE_QDRANT__HOST=qdrant
NEUROLAKE_STORAGE__ENDPOINT=minio:9000
```

## Usage Examples

### Basic Access

```python
from neurolake.config import get_settings

settings = get_settings()
db_url = settings.database.connection_string
bucket = settings.storage.data_bucket
```

### Reload Settings

```python
from neurolake.config import reload_settings

# Force reload from environment
settings = reload_settings()
```

### Testing

```python
import os
from neurolake.config import reload_settings

os.environ["NEUROLAKE_DATABASE__HOST"] = "test-db"
settings = reload_settings()
assert settings.database.host == "test-db"
```

## See Also

- `.env.example` - Example configuration file
- `neurolake/config/settings.py` - Settings implementation
- Docker Compose configuration

---

**Last Updated**: November 1, 2025
