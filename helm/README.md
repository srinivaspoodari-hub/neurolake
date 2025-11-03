# NeuroLake Helm Chart

Official Helm chart for deploying NeuroLake on Kubernetes.

## Prerequisites

- Kubernetes 1.27+
- Helm 3.12+
- PV provisioner support in the underlying infrastructure
- PostgreSQL (can be deployed with this chart or external)
- Redis (can be deployed with this chart or external)

## Installation

### Add Helm Repository

```bash
# Add NeuroLake Helm repository (when published)
helm repo add neurolake https://charts.neurolake.dev
helm repo update
```

### Install from Local Chart

```bash
# Install from local directory
cd helm
helm install neurolake ./neurolake \
  --namespace neurolake \
  --create-namespace
```

### Install with Custom Values

```bash
# Create custom values file
cat > custom-values.yaml <<EOF
api:
  replicaCount: 5
  resources:
    limits:
      memory: "4Gi"
      cpu: "2000m"

postgresql:
  auth:
    password: "my-secure-password"

ingress:
  enabled: true
  hosts:
    - host: neurolake.mycompany.com
      paths:
        - path: /
          service: frontend
        - path: /api
          service: api
EOF

# Install with custom values
helm install neurolake ./neurolake \
  --namespace neurolake \
  --create-namespace \
  --values custom-values.yaml
```

## Configuration

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.replicaCount` | Number of API replicas | `3` |
| `api.image.repository` | API image repository | `neurolake/api` |
| `api.image.tag` | API image tag | `latest` |
| `api.resources.requests.memory` | API memory request | `512Mi` |
| `api.resources.limits.memory` | API memory limit | `2Gi` |
| `api.autoscaling.enabled` | Enable HPA for API | `false` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.image.repository` | Frontend image repository | `neurolake/frontend` |
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `postgresql.auth.database` | PostgreSQL database name | `neurolake` |
| `postgresql.auth.username` | PostgreSQL username | `neurolake` |
| `postgresql.primary.persistence.size` | PostgreSQL storage size | `20Gi` |
| `redis.enabled` | Deploy Redis | `true` |
| `redis.master.persistence.size` | Redis storage size | `8Gi` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts` | Ingress hosts configuration | `[]` |
| `persistence.data.size` | Data PVC size | `50Gi` |

### Full Values

See [values.yaml](./neurolake/values.yaml) for all available configuration options.

## Usage Examples

### Basic Installation

```bash
helm install neurolake ./neurolake -n neurolake --create-namespace
```

### With External Database

```bash
helm install neurolake ./neurolake \
  --set postgresql.enabled=false \
  --set config.DB_HOST=external-postgres.example.com \
  --set secrets.DB_PASSWORD=secure-password \
  -n neurolake --create-namespace
```

### With Autoscaling

```bash
helm install neurolake ./neurolake \
  --set api.autoscaling.enabled=true \
  --set api.autoscaling.minReplicas=3 \
  --set api.autoscaling.maxReplicas=10 \
  -n neurolake --create-namespace
```

### With Ingress

```bash
helm install neurolake ./neurolake \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=neurolake.example.com \
  --set ingress.tls[0].secretName=neurolake-tls \
  --set ingress.tls[0].hosts[0]=neurolake.example.com \
  -n neurolake --create-namespace
```

### Production Configuration

```bash
helm install neurolake ./neurolake \
  --set api.replicaCount=5 \
  --set api.autoscaling.enabled=true \
  --set postgresql.primary.persistence.size=100Gi \
  --set persistence.data.size=500Gi \
  --set ingress.enabled=true \
  --set monitoring.enabled=true \
  --values production-secrets.yaml \
  -n neurolake --create-namespace
```

## Upgrading

```bash
# Upgrade with new image version
helm upgrade neurolake ./neurolake \
  --set api.image.tag=v1.1.0 \
  --set frontend.image.tag=v1.1.0 \
  -n neurolake

# Upgrade with new values file
helm upgrade neurolake ./neurolake \
  --values new-values.yaml \
  -n neurolake

# Check upgrade status
helm status neurolake -n neurolake
```

## Rollback

```bash
# View release history
helm history neurolake -n neurolake

# Rollback to previous release
helm rollback neurolake -n neurolake

# Rollback to specific revision
helm rollback neurolake 2 -n neurolake
```

## Uninstallation

```bash
# Uninstall release (keeps PVCs)
helm uninstall neurolake -n neurolake

# Delete namespace and all resources
kubectl delete namespace neurolake
```

## Secrets Management

### Using External Secrets

For production, use external secret management:

```yaml
# external-secrets.yaml
api:
  envFrom:
    - secretRef:
        name: neurolake-external-secrets

postgresql:
  auth:
    existingSecret: postgres-credentials
```

### Using Sealed Secrets

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
echo -n my-secret-password | kubectl create secret generic neurolake-secrets \
  --dry-run=client \
  --from-file=DB_PASSWORD=/dev/stdin \
  -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

kubectl apply -f sealed-secret.yaml -n neurolake
```

## Monitoring

### Prometheus Integration

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s

  prometheusRule:
    enabled: true
```

### Grafana Dashboards

Import NeuroLake Grafana dashboards from:
- API metrics: `grafana/api-dashboard.json`
- System metrics: `grafana/system-dashboard.json`

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n neurolake
kubectl describe pod <pod-name> -n neurolake
kubectl logs -f <pod-name> -n neurolake
```

### Common Issues

#### Pods Not Starting

```bash
# Check events
kubectl get events -n neurolake --sort-by='.lastTimestamp'

# Check resource constraints
kubectl top pods -n neurolake
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n neurolake -- \
  psql -h neurolake-postgresql -U neurolake -d neurolake
```

#### Image Pull Errors

```bash
# Check image pull secrets
kubectl get secrets -n neurolake

# Create docker registry secret
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.io \
  --docker-username=your-username \
  --docker-password=your-password \
  -n neurolake
```

## Development

### Testing Changes

```bash
# Lint chart
helm lint ./neurolake

# Template chart (dry-run)
helm template neurolake ./neurolake --debug

# Install with dry-run
helm install neurolake ./neurolake --dry-run --debug -n neurolake
```

### Packaging

```bash
# Package chart
helm package ./neurolake

# Generate index
helm repo index .
```

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## Support

- Documentation: https://docs.neurolake.dev
- GitHub Issues: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev

## License

Apache 2.0 - See LICENSE file for details
