# NeuroLake Centralized Logging

Centralized logging solution for NeuroLake using Loki or ELK Stack.

## Overview

Two logging stack options:

1. **Loki Stack** (Recommended)
   - Lightweight, cost-effective
   - Integrates with Grafana
   - LogQL query language
   - Components: Loki + Promtail

2. **ELK Stack** (Full-featured)
   - Powerful search and analytics
   - Rich visualization
   - Components: Elasticsearch + Kibana + Filebeat

## Quick Start

### Option 1: Loki Stack (Recommended)

```bash
# Add Grafana Helm repo
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create logging namespace
kubectl create namespace logging

# Install Loki stack
helm install loki grafana/loki-stack \
  --namespace logging \
  --values loki-values.yaml

# Wait for pods
kubectl wait --namespace logging \
  --for=condition=ready pod \
  --selector=app=loki \
  --timeout=300s

# Add Loki datasource to Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Navigate to Configuration > Data Sources > Add Loki
# URL: http://loki.logging.svc.cluster.local:3100
```

### Option 2: ELK Stack

```bash
# Add Elastic Helm repo
helm repo add elastic https://helm.elastic.co
helm repo update

# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --values elasticsearch-values.yaml

# Wait for Elasticsearch
kubectl wait --namespace logging \
  --for=condition=ready pod \
  --selector=app=elasticsearch-master \
  --timeout=600s

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set elasticsearchHosts=http://elasticsearch-master:9200

# Install Filebeat
helm install filebeat elastic/filebeat \
  --namespace logging \
  --values elasticsearch-values.yaml

# Access Kibana
kubectl port-forward -n logging svc/kibana-kibana 5601:5601
# Open http://localhost:5601
```

## Loki Stack Details

### Architecture

```
Pods ’ Promtail (DaemonSet) ’ Loki ’ Grafana
```

### Components

**Loki** - Log aggregation system
- Stores logs as compressed chunks
- Indexes metadata, not content
- 30-day retention (configurable)

**Promtail** - Log collector
- Runs on every node (DaemonSet)
- Discovers pods automatically
- Adds Kubernetes metadata

### Configuration

Key settings in `loki-values.yaml`:

- **Retention**: 30 days (720h)
- **Storage**: 50Gi persistent volume
- **Limits**: 10MB/s ingestion rate
- **Compaction**: Every 10 minutes

### Querying Logs

#### In Grafana

```logql
# All logs from neurolake namespace
{namespace="neurolake"}

# API logs only
{namespace="neurolake", component="api"}

# Error logs
{namespace="neurolake"} |= "ERROR"

# JSON parsing
{namespace="neurolake"} | json | level="error"

# Rate of errors
rate({namespace="neurolake"} |= "ERROR" [5m])

# Top 10 error messages
topk(10, sum by (message) (
  count_over_time({namespace="neurolake"} |= "ERROR" [1h])
))
```

#### LogQL Examples

```logql
# Filter by pod
{pod="neurolake-api-abc123"}

# Multiple filters
{namespace="neurolake", component="api"} |= "database" != "health"

# Regular expressions
{namespace="neurolake"} |~ "error|failed|exception"

# Line format
{namespace="neurolake"} | line_format "{{.timestamp}} {{.message}}"

# Label extraction
{namespace="neurolake"} | json | level="error" | line_format "{{.user_id}}"

# Aggregations
sum(rate({namespace="neurolake"}[5m])) by (component)
```

## ELK Stack Details

### Architecture

```
Pods ’ Filebeat (DaemonSet) ’ [Logstash] ’ Elasticsearch ’ Kibana
```

### Components

**Elasticsearch** - Search and analytics engine
- 3-node cluster (master + data)
- 100Gi storage per node
- Index lifecycle management

**Kibana** - Visualization and search UI
- 2 replicas for HA
- Rich dashboards and visualizations

**Filebeat** - Log shipper
- Lightweight collector
- Kubernetes metadata enrichment

**Logstash** (Optional) - Log processing
- Advanced filtering and transformation
- Multiple input/output plugins

### Index Patterns

- `neurolake-api-YYYY.MM.DD` - API logs
- `neurolake-frontend-YYYY.MM.DD` - Frontend logs
- `neurolake-worker-YYYY.MM.DD` - Worker logs
- `neurolake-system-YYYY.MM.DD` - Other logs

### Kibana Queries

#### KQL (Kibana Query Language)

```kql
# Error logs
log_level: "ERROR"

# API errors
kubernetes.labels.app_kubernetes_io_component: "api" AND log_level: "ERROR"

# Time range
@timestamp >= "now-1h"

# User actions
json_data.user_id: "12345" AND json_data.action: "query"

# Wildcards
message: *database*

# Boolean operators
(log_level: "ERROR" OR log_level: "CRITICAL") AND kubernetes.namespace: "neurolake"
```

#### Lucene Syntax

```
# Field search
status:500

# Range
response_time:[100 TO 500]

# Wildcards
message:data*

# Regex
message:/error|exception/

# Exists
_exists_:user_id
```

## Application Logging

### Python (Structured JSON Logs)

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)

# Configure logger
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("neurolake")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Usage
logger.info("User logged in", extra={"user_id": "12345", "ip": "1.2.3.4"})
logger.error("Database connection failed", extra={"database": "postgres"})
```

### FastAPI Logging Middleware

```python
from fastapi import FastAPI, Request
import time
import uuid

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Add request ID to context
    request.state.request_id = request_id

    # Log request
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
        }
    )

    # Process request
    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
    )

    return response
```

## Log Retention

### Loki

Configured in `loki-values.yaml`:

```yaml
table_manager:
  retention_deletes_enabled: true
  retention_period: 720h  # 30 days
```

### Elasticsearch

Index Lifecycle Management (ILM):

```bash
# Create ILM policy
curl -X PUT "http://elasticsearch:9200/_ilm/policy/neurolake-logs" -H 'Content-Type: application/json' -d'
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_size": "50gb"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
'
```

## Alerting on Logs

### Loki Alerts (via Prometheus)

```yaml
# In prometheus-values.yaml
additionalPrometheusRulesMap:
  loki-alerts:
    groups:
      - name: logs
        rules:
          - alert: HighErrorRate
            expr: |
              sum(rate({namespace="neurolake"} |= "ERROR" [5m])) > 10
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High error rate in logs"
              description: "Error rate is {{ $value }} per second"
```

### Elasticsearch Watcher

```json
{
  "trigger": {
    "schedule": {
      "interval": "5m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["neurolake-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {"term": {"log_level": "ERROR"}},
                {"range": {"@timestamp": {"gte": "now-5m"}}}
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total": {
        "gt": 100
      }
    }
  },
  "actions": {
    "notify_slack": {
      "webhook": {
        "scheme": "https",
        "host": "hooks.slack.com",
        "port": 443,
        "method": "post",
        "path": "/services/YOUR/WEBHOOK/URL",
        "body": "High error rate detected: {{ctx.payload.hits.total}} errors in last 5 minutes"
      }
    }
  }
}
```

## Troubleshooting

### Loki Not Receiving Logs

```bash
# Check Promtail pods
kubectl get pods -n logging -l app=promtail

# Check Promtail logs
kubectl logs -n logging -l app=promtail -f

# Verify Promtail is discovering pods
kubectl exec -n logging -it $(kubectl get pod -n logging -l app=promtail -o name | head -1) -- wget -O- http://localhost:3101/targets

# Test Loki API
kubectl port-forward -n logging svc/loki 3100:3100
curl http://localhost:3100/ready
```

### Elasticsearch Issues

```bash
# Check cluster health
kubectl exec -n logging elasticsearch-master-0 -- curl -s http://localhost:9200/_cluster/health?pretty

# Check indices
kubectl exec -n logging elasticsearch-master-0 -- curl -s http://localhost:9200/_cat/indices?v

# Check disk space
kubectl exec -n logging elasticsearch-master-0 -- df -h

# Check allocation
kubectl exec -n logging elasticsearch-master-0 -- curl -s http://localhost:9200/_cat/allocation?v
```

### High Storage Usage

```bash
# Loki - reduce retention
helm upgrade loki grafana/loki-stack \
  --set loki.config.table_manager.retention_period=360h \
  -n logging

# Elasticsearch - delete old indices
kubectl exec -n logging elasticsearch-master-0 -- curl -X DELETE http://localhost:9200/neurolake-*-2024.01.*
```

## Best Practices

1. **Use Structured Logging** - JSON format for easy parsing
2. **Add Context** - Include request_id, user_id, trace_id
3. **Set Log Levels** - DEBUG for development, INFO+ for production
4. **Avoid Logging Secrets** - Never log passwords, tokens, API keys
5. **Use Sampling** - For high-volume logs, sample debug logs
6. **Retention Policy** - Balance storage cost vs. compliance
7. **Index Patterns** - Separate indices by service/component
8. **Regular Cleanup** - Automate old log deletion
9. **Monitor Storage** - Alert on disk space
10. **Test Queries** - Ensure logs are searchable

## Comparison: Loki vs ELK

| Feature | Loki | ELK |
|---------|------|-----|
| **Storage** | 50GB for 30 days | 300GB for 30 days |
| **Search** | LogQL (regex) | Full-text search |
| **Performance** | Fast for time-range | Fast for complex queries |
| **Cost** | Low | High |
| **Complexity** | Simple | Complex |
| **Visualization** | Grafana | Kibana |
| **Best For** | Kubernetes logs | Advanced analytics |

## Next Steps

1. **Task 270:** Create CI/CD pipeline (GitHub Actions)
2. Configure log-based alerts
3. Create log retention policies
4. Set up log archival to S3

## Resources

- [Loki Documentation](https://grafana.com/docs/loki/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [LogQL Cheat Sheet](https://grafana.com/docs/loki/latest/logql/)
- [KQL Documentation](https://www.elastic.co/guide/en/kibana/current/kuery-query.html)

## Support

- GitHub: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev
