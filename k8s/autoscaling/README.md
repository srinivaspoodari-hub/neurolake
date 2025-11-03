# NeuroLake Autoscaling Configuration

This directory contains autoscaling configurations for automatically adjusting NeuroLake resources based on load.

## Overview

Kubernetes provides two types of autoscaling:

1. **Horizontal Pod Autoscaler (HPA)** - Scales the number of pod replicas
2. **Vertical Pod Autoscaler (VPA)** - Adjusts CPU and memory requests/limits

## Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured
- Metrics Server installed (for HPA)
- VPA operator installed (for VPA, optional)

## Installation

### 1. Install Metrics Server

Metrics Server collects resource metrics for HPA:

```bash
# Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For local/development clusters (minikube, kind), may need insecure TLS:
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Wait for metrics-server to be ready
kubectl wait --namespace kube-system \
  --for=condition=ready pod \
  --selector=k8s-app=metrics-server \
  --timeout=120s

# Verify metrics are available
kubectl top nodes
kubectl top pods -n neurolake
```

### 2. Install VPA (Optional)

Vertical Pod Autoscaler for optimizing resource requests:

```bash
# Clone VPA repository
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler

# Install VPA
./hack/vpa-up.sh

# Verify VPA components
kubectl get pods -n kube-system | grep vpa

# Expected pods:
# - vpa-admission-controller
# - vpa-recommender
# - vpa-updater
```

### 3. Apply HPA Configurations

```bash
# Apply Horizontal Pod Autoscalers
kubectl apply -f hpa.yaml

# Verify HPAs
kubectl get hpa -n neurolake
```

Expected output:
```
NAME                     REFERENCE                  TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
neurolake-api-hpa        Deployment/neurolake-api   45%/70%, 60%/80%   3      10        3          10s
neurolake-frontend-hpa   Deployment/neurolake-frontend 30%/75%, 40%/80% 2      8         2          10s
```

### 4. Apply VPA Configurations (Optional)

```bash
# Apply Vertical Pod Autoscalers
kubectl apply -f vpa.yaml

# Verify VPAs
kubectl get vpa -n neurolake
```

## Configuration

### Horizontal Pod Autoscaler (HPA)

#### API Service HPA

Scales API pods from 3 to 10 based on:
- **CPU**: 70% utilization target
- **Memory**: 80% utilization target

```yaml
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Scaling Behavior:**
- **Scale Up**: Fast (100% increase or +4 pods max every 30s)
- **Scale Down**: Conservative (50% decrease or -2 pods max every 60s, 5 min stabilization)

#### Frontend Service HPA

Scales frontend pods from 2 to 8 based on CPU/memory.

#### Worker Service HPA

Scales worker pods from 2 to 20 (higher max for background jobs).

**Configuration:**
- More aggressive scale-up (faster response to workload)
- Conservative scale-down (avoid thrashing)
- Lower CPU threshold (60%) for background processing

### Vertical Pod Autoscaler (VPA)

#### Update Modes

**Auto** - VPA automatically updates pods (evicts and recreates):
```yaml
updatePolicy:
  updateMode: "Auto"
```
Best for: Stateless services (API, Frontend)

**Recreate** - VPA evicts pods to apply updates:
```yaml
updatePolicy:
  updateMode: "Recreate"
```
Best for: Services that can tolerate restarts

**Initial** - VPA only sets resources on pod creation:
```yaml
updatePolicy:
  updateMode: "Initial"
```
Best for: StatefulSets (databases, caches)

**Off** - VPA only provides recommendations:
```yaml
updatePolicy:
  updateMode: "Off"
```
Best for: Monitoring and analysis

#### Resource Constraints

Define min/max bounds for VPA:

```yaml
resourcePolicy:
  containerPolicies:
    - containerName: api
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 4000m
        memory: 8Gi
```

## Usage

### View HPA Status

```bash
# List HPAs
kubectl get hpa -n neurolake

# Detailed HPA info
kubectl describe hpa neurolake-api-hpa -n neurolake

# Watch HPA in real-time
kubectl get hpa -n neurolake -w

# View HPA events
kubectl get events -n neurolake --field-selector involvedObject.kind=HorizontalPodAutoscaler
```

### View VPA Status

```bash
# List VPAs
kubectl get vpa -n neurolake

# Detailed VPA info
kubectl describe vpa neurolake-api-vpa -n neurolake

# View VPA recommendations
kubectl get vpa neurolake-api-vpa -n neurolake -o jsonpath='{.status.recommendation}'

# View VPA in YAML format
kubectl get vpa neurolake-api-vpa -n neurolake -o yaml
```

### View Current Resource Usage

```bash
# Node metrics
kubectl top nodes

# Pod metrics
kubectl top pods -n neurolake

# Specific pod metrics
kubectl top pod <pod-name> -n neurolake --containers
```

## Testing Autoscaling

### Load Testing HPA

#### Method 1: Using Apache Bench

```bash
# Get API service URL
API_URL=$(kubectl get ingress neurolake-ingress -n neurolake -o jsonpath='{.spec.rules[0].host}')

# Generate load (100 concurrent requests, 10000 total)
ab -n 10000 -c 100 https://$API_URL/api/health

# Watch scaling in another terminal
kubectl get hpa neurolake-api-hpa -n neurolake -w
```

#### Method 2: Using hey

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Generate load (100 QPS for 5 minutes)
hey -z 5m -q 100 https://$API_URL/api/health

# Monitor scaling
watch kubectl get pods -n neurolake -l app.kubernetes.io/component=api
```

#### Method 3: Using Kubernetes Job

```bash
# Create load generator job
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: load-generator
  namespace: neurolake
spec:
  parallelism: 10
  completions: 10
  template:
    spec:
      containers:
        - name: busybox
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              while true; do
                wget -q -O- http://neurolake-api-service:8000/health
                sleep 0.01
              done
      restartPolicy: Never
EOF

# Watch HPA scale up
kubectl get hpa neurolake-api-hpa -n neurolake -w

# Delete load generator when done
kubectl delete job load-generator -n neurolake
```

### Testing VPA

VPA requires historical data (24-48 hours) for accurate recommendations:

```bash
# View current recommendations
kubectl describe vpa neurolake-api-vpa -n neurolake

# Look for recommendation section:
# Lower Bound:
#   Cpu:     100m
#   Memory:  262144k
# Target:
#   Cpu:     250m
#   Memory:  524288k
# Upper Bound:
#   Cpu:     1000m
#   Memory:  1048576k
```

## Advanced Configuration

### Custom Metrics with Prometheus

For scaling based on custom metrics (request rate, queue depth, etc.):

#### 1. Install Prometheus Adapter

```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus adapter
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace monitoring \
  --set prometheus.url=http://prometheus-server.monitoring.svc \
  --set prometheus.port=80
```

#### 2. Configure Custom Metrics

Create a ConfigMap for custom metrics:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
      - seriesQuery: 'http_requests_total{namespace="neurolake",pod!=""}'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          matches: "^(.*)_total$"
          as: "${1}_per_second"
        metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

#### 3. Use Custom Metrics in HPA

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### Scaling Based on Queue Depth

For Celery/RabbitMQ/SQS queues:

```yaml
metrics:
  - type: External
    external:
      metric:
        name: celery_queue_depth
        selector:
          matchLabels:
            queue: default
      target:
        type: AverageValue
        averageValue: "50"  # Scale when 50 jobs per pod
```

### Predictive Autoscaling

Using KEDA (Kubernetes Event-Driven Autoscaling):

```bash
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace

# Example: Scale based on Prometheus metrics
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: neurolake-api-scaledobject
  namespace: neurolake
spec:
  scaleTargetRef:
    name: neurolake-api
  minReplicaCount: 3
  maxReplicaCount: 10
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus-server.monitoring.svc
        metricName: http_requests_per_second
        threshold: '1000'
        query: |
          sum(rate(http_requests_total{job="neurolake-api"}[2m]))
```

## Best Practices

### HPA Best Practices

1. **Set Appropriate Targets:**
   - CPU: 60-80% utilization
   - Memory: 70-85% utilization
   - Lower targets = more pods, higher cost
   - Higher targets = better utilization, risk of saturation

2. **Configure Scaling Behavior:**
   - Fast scale-up for responsiveness
   - Slow scale-down for stability
   - Use stabilization windows to prevent flapping

3. **Resource Requests Must Be Set:**
   - HPA requires resource requests defined
   - Requests should be based on typical usage
   - Use VPA recommendations to tune requests

4. **Don't Mix HPA and VPA:**
   - Don't use HPA and VPA on the same metrics
   - HPA scales horizontally (more pods)
   - VPA scales vertically (bigger pods)
   - Use HPA for CPU/memory, VPA in "Off" mode for recommendations

5. **Monitor Scaling Events:**
   - Set up alerts for excessive scaling
   - Track scaling frequency
   - Investigate oscillation patterns

### VPA Best Practices

1. **Start with Recommendations:**
   - Use `updateMode: Off` initially
   - Collect recommendations for 24-48 hours
   - Review recommendations before enabling auto-update

2. **Use Appropriate Update Modes:**
   - `Auto` for stateless services
   - `Initial` for StatefulSets
   - `Off` for production databases

3. **Set Resource Bounds:**
   - Always set minAllowed and maxAllowed
   - Prevent over-provisioning
   - Account for node capacity

4. **Consider Pod Disruption:**
   - VPA evicts pods to update resources
   - Use PodDisruptionBudgets (PDB)
   - Schedule updates during low-traffic periods

5. **Combine with Cluster Autoscaler:**
   - Cluster Autoscaler adds/removes nodes
   - VPA adjusts pod sizes
   - Together they optimize cluster resources

### General Autoscaling Best Practices

1. **Load Testing:**
   - Test autoscaling before production
   - Verify scale-up and scale-down behavior
   - Measure scaling latency

2. **Monitoring:**
   - Track pod count over time
   - Monitor resource utilization
   - Alert on scaling failures

3. **Cost Optimization:**
   - Balance performance and cost
   - Use spot/preemptible instances for workers
   - Scale down aggressively during off-hours

4. **Capacity Planning:**
   - Ensure cluster has capacity for scale-up
   - Use Cluster Autoscaler for node scaling
   - Set appropriate maxReplicas based on cluster size

## Monitoring

### HPA Metrics

Key metrics to monitor:

```promql
# Current replica count
kube_horizontalpodautoscaler_status_current_replicas{namespace="neurolake"}

# Desired replica count
kube_horizontalpodautoscaler_status_desired_replicas{namespace="neurolake"}

# CPU utilization vs target
kube_horizontalpodautoscaler_status_current_metrics{metric_name="cpu",namespace="neurolake"}

# Scaling events
rate(kube_horizontalpodautoscaler_spec_max_replicas{namespace="neurolake"}[5m])
```

### Grafana Dashboard

Import HPA dashboard (ID: 12114) or create custom:

```json
{
  "dashboard": {
    "title": "NeuroLake Autoscaling",
    "panels": [
      {
        "title": "API Pod Count",
        "targets": [
          {
            "expr": "kube_deployment_status_replicas{deployment='neurolake-api'}"
          }
        ]
      },
      {
        "title": "CPU Utilization",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total{namespace='neurolake'}[5m]) * 100"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting

### HPA Not Scaling

```bash
# Check HPA conditions
kubectl describe hpa neurolake-api-hpa -n neurolake

# Common issues:
# 1. Metrics not available
kubectl top pods -n neurolake

# 2. Resource requests not set
kubectl get deployment neurolake-api -n neurolake -o yaml | grep -A 5 resources

# 3. Metrics server not running
kubectl get pods -n kube-system -l k8s-app=metrics-server

# 4. HPA controller errors
kubectl logs -n kube-system -l app=kube-controller-manager | grep HorizontalPodAutoscaler
```

### VPA Not Updating Pods

```bash
# Check VPA status
kubectl describe vpa neurolake-api-vpa -n neurolake

# Common issues:
# 1. VPA components not running
kubectl get pods -n kube-system | grep vpa

# 2. Not enough historical data
# Wait 24-48 hours for recommendations

# 3. Update mode set to "Off"
kubectl get vpa neurolake-api-vpa -n neurolake -o jsonpath='{.spec.updatePolicy.updateMode}'

# 4. PodDisruptionBudget preventing eviction
kubectl get pdb -n neurolake
```

### Scaling Flapping

Rapid scale-up and scale-down:

```bash
# Increase stabilization window
kubectl patch hpa neurolake-api-hpa -n neurolake --type='json' -p='[
  {"op": "replace", "path": "/spec/behavior/scaleDown/stabilizationWindowSeconds", "value": 600}
]'

# Adjust target utilization
kubectl patch hpa neurolake-api-hpa -n neurolake --type='json' -p='[
  {"op": "replace", "path": "/spec/metrics/0/resource/target/averageUtilization", "value": 75}
]'
```

## Next Steps

1. **Task 268:** Set up monitoring (Prometheus) for metrics collection
2. **Task 269:** Set up logging (Loki/ELK) for centralized logs
3. **Task 270:** Create CI/CD pipeline (GitHub Actions) for automated deployments

## Resources

- [HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [VPA Documentation](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [KEDA](https://keda.sh/)
- [Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)

## Support

For issues related to NeuroLake autoscaling:
- GitHub: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev
