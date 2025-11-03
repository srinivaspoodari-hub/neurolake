# NeuroLake Ingress Configuration

This directory contains ingress controller configurations for routing external HTTP/HTTPS traffic to NeuroLake services.

## Overview

The ingress setup provides:
- **Production ingress** with TLS/SSL, security headers, rate limiting
- **Development/staging ingress** for HTTP-only testing
- **Admin ingress** with basic authentication for monitoring tools
- **NGINX ingress controller** configuration with optimized settings

## Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured to access your cluster
- Helm 3.12+ (for NGINX ingress controller installation)
- cert-manager (for TLS certificate management)
- Domain name(s) pointing to your cluster's load balancer

## Installation

### 1. Install NGINX Ingress Controller

```bash
# Add NGINX Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install NGINX ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.admissionWebhooks.patch.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.type=LoadBalancer \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254

# Wait for the controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### 2. Install cert-manager (for TLS)

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=120s
```

### 3. Apply NGINX Configuration

```bash
# Apply NGINX ingress controller ConfigMap
kubectl apply -f ingress-nginx-config.yaml

# Restart NGINX ingress controller to pick up new config
kubectl rollout restart deployment ingress-nginx-controller -n ingress-nginx
```

### 4. Deploy NeuroLake Ingress Resources

#### For Production (with TLS):

```bash
# First, update the hosts in ingress.yaml to match your domain
# Replace 'neurolake.example.com' with your actual domain

# Apply the ingress configuration
kubectl apply -f ingress.yaml

# Check ingress status
kubectl get ingress -n neurolake
kubectl describe ingress neurolake-ingress -n neurolake
```

#### For Development (HTTP only):

```bash
# Add local DNS entry (for local testing)
echo "127.0.0.1 dev.neurolake.local" | sudo tee -a /etc/hosts

# Apply dev ingress
kubectl apply -f ingress.yaml  # This includes dev ingress

# Port forward to ingress controller (if not using LoadBalancer)
kubectl port-forward --namespace ingress-nginx service/ingress-nginx-controller 8080:80
```

## Configuration

### Ingress Types

This setup includes three ingress configurations:

#### 1. Production Ingress (`neurolake-ingress`)

**Hosts:**
- `neurolake.example.com` - Main application (frontend + API)
- `api.neurolake.example.com` - API-only subdomain

**Features:**
- TLS/SSL with cert-manager (Let's Encrypt)
- CORS enabled with credential support
- Rate limiting (100 RPS, 10 concurrent connections)
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- WebSocket support for API
- 50MB request body size limit

**Routes:**
- `/` ’ Frontend service (port 3000)
- `/api` ’ API service (port 8000)
- `/docs` ’ API documentation (port 8000)
- `/health` ’ Health check endpoint (port 8000)

#### 2. Development Ingress (`neurolake-ingress-dev`)

**Host:**
- `dev.neurolake.local` - Local development

**Features:**
- HTTP only (no TLS)
- CORS enabled
- 50MB request body size limit

**Routes:**
- `/` ’ Frontend service
- `/api` ’ API service

#### 3. Admin Ingress (`neurolake-ingress-admin`)

**Host:**
- `admin.neurolake.example.com` - Admin/monitoring services

**Features:**
- TLS/SSL with cert-manager
- HTTP Basic Authentication (requires secret)
- Protected access to monitoring tools

**Routes:**
- `/grafana` ’ Grafana (port 3000)
- `/prometheus` ’ Prometheus (port 9090)
- `/jaeger` ’ Jaeger tracing (port 16686)

### Customizing Domains

Edit `ingress.yaml` and replace all instances of:
- `neurolake.example.com` ’ Your production domain
- `api.neurolake.example.com` ’ Your API subdomain
- `admin.neurolake.example.com` ’ Your admin subdomain
- `dev.neurolake.local` ’ Your development domain

### Rate Limiting

Adjust rate limits in ingress annotations:

```yaml
nginx.ingress.kubernetes.io/limit-rps: "100"      # Requests per second
nginx.ingress.kubernetes.io/limit-connections: "10"  # Concurrent connections
```

### Security Headers

Security headers are configured in the `configuration-snippet`:

```yaml
nginx.ingress.kubernetes.io/configuration-snippet: |
  more_set_headers "X-Frame-Options: SAMEORIGIN";
  more_set_headers "X-Content-Type-Options: nosniff";
  more_set_headers "X-XSS-Protection: 1; mode=block";
  more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
  more_set_headers "Permissions-Policy: geolocation=(), microphone=(), camera=()";
```

### TLS Configuration

The ingress uses cert-manager with Let's Encrypt for automatic TLS certificates.

**ClusterIssuer Configuration** (see Task 266 for full setup):

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

## Usage Examples

### Basic Access

```bash
# Access production application
curl https://neurolake.example.com/health

# Access API directly
curl https://api.neurolake.example.com/health

# Access API through main domain
curl https://neurolake.example.com/api/health

# Access API documentation
curl https://neurolake.example.com/docs
```

### Testing with Port Forwarding

```bash
# Port forward ingress controller
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80 8443:443

# Test locally
curl http://localhost:8080/health -H "Host: dev.neurolake.local"
```

### Admin Access (with Basic Auth)

First, create the basic auth secret:

```bash
# Create htpasswd file
htpasswd -c auth admin

# Create Kubernetes secret
kubectl create secret generic basic-auth \
  --from-file=auth \
  -n neurolake

# Access admin services
curl -u admin:password https://admin.neurolake.example.com/grafana
```

## Monitoring

### Check Ingress Status

```bash
# List all ingresses
kubectl get ingress -n neurolake

# Detailed ingress info
kubectl describe ingress neurolake-ingress -n neurolake

# Check ingress controller logs
kubectl logs -f -n ingress-nginx -l app.kubernetes.io/component=controller
```

### View TLS Certificates

```bash
# List certificates
kubectl get certificates -n neurolake

# Check certificate details
kubectl describe certificate neurolake-tls-secret -n neurolake

# View certificate secret
kubectl get secret neurolake-tls-secret -n neurolake -o yaml
```

### NGINX Metrics

NGINX ingress controller exposes Prometheus metrics on port 10254:

```bash
# Port forward metrics endpoint
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller-metrics 10254:10254

# View metrics
curl http://localhost:10254/metrics
```

## Troubleshooting

### Ingress Not Working

```bash
# Check ingress controller status
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Check ingress resource
kubectl get ingress -n neurolake
kubectl describe ingress neurolake-ingress -n neurolake

# Check service endpoints
kubectl get endpoints -n neurolake
```

### TLS Certificate Issues

```bash
# Check certificate status
kubectl get certificates -n neurolake
kubectl describe certificate neurolake-tls-secret -n neurolake

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager

# Check certificate request
kubectl get certificaterequest -n neurolake
kubectl describe certificaterequest <name> -n neurolake

# Check ACME challenge
kubectl get challenges -n neurolake
kubectl describe challenge <name> -n neurolake
```

### DNS Issues

```bash
# Check DNS resolution
nslookup neurolake.example.com

# Check load balancer external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Test with curl
curl -v https://neurolake.example.com/health
```

### 404 Errors

```bash
# Check backend service
kubectl get svc -n neurolake
kubectl describe svc neurolake-api-service -n neurolake

# Check pod status
kubectl get pods -n neurolake
kubectl logs -f -n neurolake -l app.kubernetes.io/component=api

# Test service directly (bypass ingress)
kubectl port-forward -n neurolake svc/neurolake-api-service 8000:8000
curl http://localhost:8000/health
```

### Rate Limiting Issues

```bash
# Check ingress annotations
kubectl get ingress neurolake-ingress -n neurolake -o yaml | grep limit

# Test rate limiting
for i in {1..150}; do curl -s https://neurolake.example.com/api/health; done

# Check NGINX error logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller | grep limit
```

### CORS Issues

```bash
# Test CORS with preflight request
curl -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  https://neurolake.example.com/api/endpoint

# Check CORS headers
curl -I https://neurolake.example.com/api/health
```

## Security Best Practices

1. **TLS/SSL:**
   - Always use TLS in production
   - Use strong cipher suites (configured in ingress-nginx-config.yaml)
   - Enable HSTS headers
   - Use TLS 1.2 or higher

2. **Authentication:**
   - Use basic auth for admin endpoints
   - Consider integrating OAuth2/OIDC for user authentication
   - Rotate credentials regularly

3. **Rate Limiting:**
   - Implement rate limiting to prevent abuse
   - Adjust limits based on your traffic patterns
   - Monitor rate limit metrics

4. **Security Headers:**
   - Enable all security headers (X-Frame-Options, CSP, etc.)
   - Customize Content-Security-Policy for your application

5. **Network Policies:**
   - Implement Kubernetes network policies to restrict traffic
   - Limit ingress controller access to specific namespaces

6. **Monitoring:**
   - Enable Prometheus metrics
   - Set up alerts for certificate expiration
   - Monitor 4xx/5xx error rates

## Cloud Provider Specific Notes

### AWS (EKS)

```bash
# Use NLB for better performance
--set controller.service.type=LoadBalancer \
--set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"=nlb

# Use AWS Certificate Manager
--set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-ssl-cert"=arn:aws:acm:...
```

### GCP (GKE)

```bash
# Use GCP Load Balancer
--set controller.service.type=LoadBalancer

# Use Google-managed certificates
kubectl apply -f managed-certificate.yaml
```

### Azure (AKS)

```bash
# Use Azure Load Balancer
--set controller.service.type=LoadBalancer

# Use Azure Application Gateway
# Consider using Azure Application Gateway Ingress Controller instead
```

## Performance Tuning

### NGINX Configuration

Key performance settings in `ingress-nginx-config.yaml`:

- `worker-processes: auto` - Match CPU cores
- `max-worker-connections: 16384` - Concurrent connections per worker
- `upstream-keepalive-connections: 50` - Backend connection pooling
- `gzip-level: 5` - Compression (balance speed vs. size)

### Resource Limits

Adjust NGINX controller resources based on traffic:

```bash
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --set controller.resources.requests.cpu=500m \
  --set controller.resources.requests.memory=512Mi \
  --set controller.resources.limits.cpu=2000m \
  --set controller.resources.limits.memory=2Gi \
  -n ingress-nginx
```

## Advanced Configuration

### Custom Error Pages

```yaml
# In ingress-nginx-config.yaml
custom-http-errors: "404,503"
default-backend-service: "neurolake/custom-error-pages"
```

### ModSecurity WAF

Enable Web Application Firewall:

```yaml
enable-modsecurity: "true"
enable-owasp-modsecurity-crs: "true"
```

### External Authentication

Integrate with OAuth2 proxy or other auth providers:

```yaml
nginx.ingress.kubernetes.io/auth-url: "https://auth.example.com/oauth2/auth"
nginx.ingress.kubernetes.io/auth-signin: "https://auth.example.com/oauth2/start"
```

## Next Steps

1. **Task 266:** Set up TLS/SSL certificates with cert-manager
2. **Task 267:** Configure autoscaling (HPA) for ingress controller
3. **Task 268:** Set up monitoring (Prometheus) for ingress metrics
4. **Task 269:** Set up logging (Loki) for ingress access logs

## Resources

- [NGINX Ingress Controller Documentation](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Kubernetes Ingress Documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

## Support

For issues related to NeuroLake ingress configuration:
- GitHub: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev
