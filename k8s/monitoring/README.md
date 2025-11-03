# NeuroLake Monitoring with Prometheus & Grafana

Comprehensive monitoring stack for NeuroLake using Prometheus, Grafana, and Alertmanager.

## Overview

- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization and dashboards
- **Alertmanager** - Alert routing and notifications
- **ServiceMonitors** - Automatic service discovery
- **Exporters** - Metrics for PostgreSQL, Redis, NGINX, etc.

## Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured
- Helm 3.12+
- 20GB+ storage for metrics retention

## Quick Start

```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values prometheus-values.yaml

# Wait for pods to be ready
kubectl wait --namespace monitoring \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=prometheus \
  --timeout=300s

# Apply ServiceMonitors
kubectl apply -f servicemonitors.yaml

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Open http://localhost:3000 (admin/admin)
```

## Configuration

### Prometheus Values

Key settings in `prometheus-values.yaml`:

- **Retention**: 30 days, 50GB max
- **Replicas**: 2 (HA)
- **Storage**: 100Gi persistent volume
- **Scrape interval**: 30s
- **Alert rules**: API errors, latency, resource usage

### ServiceMonitors

Automatic discovery for:
- NeuroLake API (`/metrics`)
- Frontend (`/metrics`)
- PostgreSQL exporter
- Redis exporter
- NGINX Ingress
- cert-manager
- MinIO

## Accessing Services

### Grafana

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Get admin password
kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode

# URL: http://localhost:3000
```

### Prometheus

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# URL: http://localhost:9090
```

### Alertmanager

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093

# URL: http://localhost:9093
```

## Adding Custom Metrics

### In Python (FastAPI)

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    with request_duration.time():
        response = await call_next(request)
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    return response

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

### ServiceMonitor for Custom App

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app
  namespace: neurolake
  labels:
    prometheus: neurolake
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

## Alert Configuration

### Adding Slack Notifications

```yaml
# In prometheus-values.yaml
alertmanager:
  config:
    global:
      slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    receivers:
      - name: 'slack'
        slack_configs:
          - channel: '#alerts'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Adding PagerDuty

```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .GroupLabels.alertname }}'
```

## Pre-configured Alerts

- **HighAPIErrorRate**: >5% 5xx responses for 5min
- **HighAPILatency**: p95 >1s for 5min
- **APIDown**: Service unavailable for 1min
- **HighDatabaseConnectionUsage**: >80% connections
- **HighMemoryUsage**: >90% node memory
- **HighCPUUsage**: >80% node CPU
- **DiskSpaceLow**: <10% disk space
- **PodCrashLooping**: Frequent restarts
- **PodNotReady**: Pod not running/ready

## Grafana Dashboards

### Pre-installed Dashboards

1. **Kubernetes Cluster** (GrafanaNet 7249)
2. **Node Exporter** (GrafanaNet 1860)
3. **PostgreSQL** (GrafanaNet 9628)
4. **Redis** (GrafanaNet 11835)

### Creating Custom Dashboard

```json
{
  "dashboard": {
    "title": "NeuroLake API Metrics",
    "panels": [{
      "title": "Request Rate",
      "targets": [{
        "expr": "rate(http_requests_total{job='neurolake-api'}[5m])"
      }]
    }]
  }
}
```

## Troubleshooting

### Prometheus Not Scraping Targets

```bash
# Check targets in Prometheus UI
# Status > Targets

# Verify ServiceMonitor
kubectl get servicemonitor -n neurolake

# Check Prometheus logs
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus -f

# Verify metrics endpoint
kubectl port-forward -n neurolake svc/neurolake-api-service 8000:8000
curl http://localhost:8000/metrics
```

### High Memory Usage

```bash
# Reduce retention
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --set prometheus.prometheusSpec.retention=15d \
  -n monitoring

# Reduce scrape frequency
# Edit prometheus-values.yaml, change interval to 60s
```

### Alerts Not Firing

```bash
# Check Prometheus rules
kubectl get prometheusrule -n monitoring

# Verify Alertmanager config
kubectl get secret prometheus-kube-prometheus-alertmanager -n monitoring -o yaml

# Test alert
# Trigger condition manually, check Alertmanager UI
```

## Exporters

### PostgreSQL Exporter

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: neurolake
  labels:
    app: postgres-exporter
spec:
  ports:
    - name: metrics
      port: 9187
  selector:
    app: postgres-exporter
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: neurolake
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
    spec:
      containers:
        - name: exporter
          image: prometheuscommunity/postgres-exporter:v0.15.0
          ports:
            - containerPort: 9187
          env:
            - name: DATA_SOURCE_NAME
              value: "postgresql://user:password@postgres:5432/neurolake?sslmode=disable"
```

### Redis Exporter

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-exporter
  namespace: neurolake
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-exporter
  template:
    metadata:
      labels:
        app: redis-exporter
    spec:
      containers:
        - name: exporter
          image: oliver006/redis_exporter:v1.55.0
          ports:
            - containerPort: 9121
          env:
            - name: REDIS_ADDR
              value: "redis:6379"
```

## Best Practices

1. **Set appropriate retention** - Balance storage vs history
2. **Use relabeling** - Drop high-cardinality metrics
3. **Configure alerting** - Don't alert on everything
4. **Regular backups** - Export Grafana dashboards
5. **Monitor the monitors** - Alert if Prometheus is down
6. **Use recording rules** - Pre-compute expensive queries
7. **Secure access** - Use authentication, TLS
8. **Test alerts** - Regularly verify alert delivery

## Metrics to Monitor

### API Service
- Request rate (RPS)
- Error rate (%)
- Latency (p50, p95, p99)
- Active connections

### Database
- Connection pool usage
- Query latency
- Cache hit rate
- Replication lag

### Resources
- CPU usage (%)
- Memory usage (%)
- Disk I/O
- Network throughput

### Business Metrics
- Active users
- Data processed (GB)
- Query execution time
- Job completion rate

## Next Steps

1. **Task 269:** Set up logging (Loki/ELK)
2. **Task 270:** Create CI/CD pipeline (GitHub Actions)

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Awesome Prometheus](https://github.com/roaldnefs/awesome-prometheus)

## Support

- GitHub: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev
