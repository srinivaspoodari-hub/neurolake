# NeuroLake TLS/SSL Certificate Management

This directory contains cert-manager configurations for automated TLS/SSL certificate management in Kubernetes.

## Overview

cert-manager automates the provisioning and renewal of TLS certificates from various certificate authorities (CAs), including:
- **Let's Encrypt** - Free automated certificates (production and staging)
- **Self-signed** - For local development
- **Custom CA** - For internal services
- **DNS providers** - For wildcard certificates

## Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured
- Helm 3.12+
- Domain name(s) with DNS control
- NGINX ingress controller installed (for HTTP-01 challenges)

## Installation

### 1. Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true \
  --set global.leaderElection.namespace=cert-manager

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=120s

# Verify installation
kubectl get pods -n cert-manager
```

Expected output:
```
NAME                                       READY   STATUS    RESTARTS   AGE
cert-manager-7d9f5c7b7b-xxxxx              1/1     Running   0          1m
cert-manager-cainjector-6d8c9c8b8b-xxxxx   1/1     Running   0          1m
cert-manager-webhook-5b5b5b5b5b-xxxxx      1/1     Running   0          1m
```

### 2. Configure ClusterIssuers

**IMPORTANT:** Before applying, update the email address in `cluster-issuer.yaml`:

```bash
# Edit cluster-issuer.yaml
sed -i 's/admin@neurolake.example.com/your-email@example.com/g' cluster-issuer.yaml

# Apply ClusterIssuers
kubectl apply -f cluster-issuer.yaml

# Verify ClusterIssuers are ready
kubectl get clusterissuers
```

Expected output:
```
NAME                  READY   AGE
letsencrypt-prod      True    10s
letsencrypt-staging   True    10s
selfsigned            True    10s
ca-issuer             False   10s  # False is OK if not using custom CA
```

### 3. Create Certificates

**IMPORTANT:** Before applying, update domain names in `certificates.yaml`:

```bash
# Replace example domains with your actual domains
sed -i 's/neurolake.example.com/your-domain.com/g' certificates.yaml
sed -i 's/api.neurolake.example.com/api.your-domain.com/g' certificates.yaml

# Apply certificate requests
kubectl apply -f certificates.yaml

# Check certificate status
kubectl get certificates -n neurolake
```

Expected output:
```
NAME                   READY   SECRET                        AGE
neurolake-tls          True    neurolake-tls-secret          30s
neurolake-admin-tls    True    neurolake-admin-tls           30s
neurolake-staging-tls  True    neurolake-staging-tls-secret  30s
```

## Configuration

### ClusterIssuers

#### Let's Encrypt Production
For trusted SSL certificates in production:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com  # CHANGE THIS!
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - http01:
          ingress:
            class: nginx
```

**Rate Limits:**
- 50 certificates per registered domain per week
- 5 duplicate certificates per week
- Always test with staging first!

#### Let's Encrypt Staging
For testing (higher rate limits, untrusted certificates):

```yaml
issuerRef:
  name: letsencrypt-staging
  kind: ClusterIssuer
```

Use staging for:
- Testing certificate configuration
- Development environments
- Frequent certificate renewals during setup

#### Self-Signed
For local development:

```yaml
issuerRef:
  name: selfsigned
  kind: ClusterIssuer
```

Certificates won't be trusted by browsers but work for testing.

### Certificates

#### Basic Certificate

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
  namespace: neurolake
spec:
  secretName: example-tls-secret
  duration: 2160h    # 90 days
  renewBefore: 360h  # Renew 15 days before expiry
  dnsNames:
    - example.com
    - www.example.com
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

#### Wildcard Certificate (requires DNS-01)

```yaml
spec:
  dnsNames:
    - "*.example.com"
    - example.com
  issuerRef:
    name: letsencrypt-cloudflare  # Must use DNS-01 solver
```

## DNS-01 Challenge Setup

Wildcard certificates require DNS-01 challenges. Configure for your DNS provider:

### Cloudflare

```bash
# Create API token secret
kubectl create secret generic cloudflare-api-token-secret \
  --from-literal=api-token=your-cloudflare-api-token \
  -n cert-manager

# Edit cluster-issuer.yaml and uncomment Cloudflare section
# Update email and zone

# Apply updated ClusterIssuer
kubectl apply -f cluster-issuer.yaml
```

### AWS Route53

```bash
# Create IAM policy for Route53
# Attach policy to service account or create access keys

kubectl create secret generic route53-credentials-secret \
  --from-literal=secret-access-key=your-secret-key \
  -n cert-manager

# Edit cluster-issuer.yaml and uncomment Route53 section
```

### Google Cloud DNS

```bash
# Create service account in GCP with DNS admin role
# Download JSON key

kubectl create secret generic clouddns-service-account \
  --from-file=service-account.json=path/to/key.json \
  -n cert-manager

# Edit cluster-issuer.yaml and uncomment Cloud DNS section
```

## Usage with Ingress

### Automatic Certificate Creation

cert-manager automatically creates certificates for ingress resources with annotations:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - example.com
      secretName: example-tls  # Will be created automatically
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: example-service
                port:
                  number: 80
```

### Manual Certificate Creation

For more control, create Certificate resources explicitly (see `certificates.yaml`).

## Monitoring & Troubleshooting

### Check Certificate Status

```bash
# List all certificates
kubectl get certificates -n neurolake

# Detailed certificate info
kubectl describe certificate neurolake-tls -n neurolake

# Check certificate secret
kubectl get secret neurolake-tls-secret -n neurolake -o yaml
```

### Check Certificate Details

```bash
# View certificate expiration
kubectl get certificate neurolake-tls -n neurolake -o jsonpath='{.status.notAfter}'

# View certificate conditions
kubectl get certificate neurolake-tls -n neurolake -o jsonpath='{.status.conditions[*]}'
```

### Debug Certificate Issues

```bash
# Check CertificateRequest
kubectl get certificaterequest -n neurolake
kubectl describe certificaterequest <name> -n neurolake

# Check Order (ACME)
kubectl get orders -n neurolake
kubectl describe order <name> -n neurolake

# Check Challenge
kubectl get challenges -n neurolake
kubectl describe challenge <name> -n neurolake

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager -f
kubectl logs -n cert-manager -l app=cert-manager-webhook -f
```

### Common Issues

#### 1. Certificate Pending/Not Ready

```bash
# Check events
kubectl describe certificate neurolake-tls -n neurolake

# Common causes:
# - DNS not pointing to cluster
# - Ingress controller not working
# - Rate limit exceeded (switch to staging)
# - Invalid email in ClusterIssuer
```

#### 2. HTTP-01 Challenge Failing

```bash
# Test HTTP challenge endpoint
curl http://your-domain.com/.well-known/acme-challenge/test

# Check ingress
kubectl get ingress -n neurolake
kubectl describe ingress neurolake-ingress -n neurolake

# Check solver pods
kubectl get pods -n neurolake -l acme.cert-manager.io/http01-solver=true
```

#### 3. DNS-01 Challenge Failing

```bash
# Check DNS propagation
dig TXT _acme-challenge.your-domain.com

# Check provider credentials
kubectl get secret cloudflare-api-token-secret -n cert-manager

# Test API access manually
```

#### 4. Certificate Expired

```bash
# Force renewal
kubectl delete certificaterequest <name> -n neurolake

# Check renewBefore setting (default: 2/3 of duration)
```

### View Certificate in Browser

```bash
# Port forward to test locally
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8443:443

# Access https://localhost:8443
# View certificate details in browser
```

## Certificate Rotation

cert-manager automatically renews certificates based on `renewBefore`:

```yaml
spec:
  duration: 2160h    # 90 days (Let's Encrypt max)
  renewBefore: 360h  # Renew 15 days before expiry (recommended)
```

**Renewal Timeline:**
- Certificate issued at T+0
- Renewal starts at T+75 days (2160h - 360h)
- Certificate expires at T+90 days

**Manual Renewal:**
```bash
# Delete CertificateRequest to trigger renewal
kubectl delete certificaterequest -n neurolake -l cert-manager.io/certificate-name=neurolake-tls
```

## Security Best Practices

1. **Email Address:**
   - Use a monitored email for Let's Encrypt notifications
   - Receives expiration warnings if auto-renewal fails

2. **Private Keys:**
   - Stored in Kubernetes secrets
   - Rotated on renewal (`rotationPolicy: Always`)
   - Use RBAC to restrict access

3. **Certificate Scope:**
   - Use specific domain names (avoid wildcards when possible)
   - Separate certificates for different services
   - Short validity periods (90 days max with Let's Encrypt)

4. **ClusterIssuer vs Issuer:**
   - ClusterIssuer: Cluster-wide, can issue for any namespace
   - Issuer: Namespace-scoped, more granular control
   - Use Issuer for multi-tenant clusters

5. **Monitoring:**
   - Set up alerts for certificate expiration
   - Monitor renewal failures
   - Track cert-manager metrics

6. **Backup:**
   - Backup CA private keys (for custom CA)
   - Backup ACME account keys
   - Document recovery procedures

## Production Checklist

Before going to production:

- [ ] Email address updated in ClusterIssuers
- [ ] Domain names updated in Certificate resources
- [ ] DNS pointing to cluster load balancer
- [ ] Tested with staging issuer first
- [ ] Verified HTTP-01 or DNS-01 challenges work
- [ ] Certificates showing READY=True
- [ ] Ingress serving HTTPS correctly
- [ ] Certificate auto-renewal tested
- [ ] Monitoring and alerts configured
- [ ] Backup procedures documented

## Advanced Configuration

### Certificate Annotations

Control certificate behavior with annotations:

```yaml
metadata:
  annotations:
    # Force renewal
    cert-manager.io/issue-temporary-certificate: "true"

    # Custom certificate duration
    cert-manager.io/duration: "2160h"

    # Custom renewal time
    cert-manager.io/renew-before: "360h"
```

### Webhook Configuration

For additional validation:

```yaml
# Install validating webhook
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configure webhook
kubectl edit validatingwebhookconfiguration cert-manager-webhook
```

### External DNS Integration

Automate DNS record creation:

```bash
# Install external-dns
helm install external-dns bitnami/external-dns \
  --set provider=cloudflare \
  --set cloudflare.apiToken=your-token
```

### Certificate Transparency Monitoring

Monitor issued certificates:

```bash
# Check certificate in CT logs
curl https://crt.sh/?q=your-domain.com
```

## Prometheus Metrics

cert-manager exposes metrics on port 9402:

```bash
# Enable ServiceMonitor
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cert-manager
  namespace: cert-manager
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: cert-manager
  endpoints:
    - port: tcp-prometheus-servicemonitor
      interval: 30s
EOF
```

**Key Metrics:**
- `certmanager_certificate_expiration_timestamp_seconds` - Certificate expiry time
- `certmanager_certificate_ready_status` - Certificate readiness
- `certmanager_http_acme_client_request_count` - ACME requests
- `certmanager_http_acme_client_request_duration_seconds` - Request latency

## Migration Guide

### From Manual Certificates

```bash
# Export existing certificate
kubectl get secret existing-tls-secret -n neurolake -o yaml > backup.yaml

# Create Certificate resource pointing to existing secret
# cert-manager will adopt and manage it

# Verify adoption
kubectl describe certificate existing-tls -n neurolake
```

### From Other Certificate Managers

```bash
# Kube-lego to cert-manager
# Update annotations from kubernetes.io/tls-acme to cert-manager.io/cluster-issuer

# cert-manager v0.x to v1.x
# Follow official migration guide
# API version changed from v1alpha2 to v1
```

## Cloud Provider Integration

### AWS EKS

```bash
# Use IRSA for Route53 access (recommended)
eksctl create iamserviceaccount \
  --name cert-manager \
  --namespace cert-manager \
  --cluster your-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/YourRoute53Policy \
  --approve
```

### GCP GKE

```bash
# Use Workload Identity
gcloud iam service-accounts create cert-manager

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member "serviceAccount:cert-manager@PROJECT_ID.iam.gserviceaccount.com" \
  --role "roles/dns.admin"

kubectl annotate serviceaccount cert-manager \
  -n cert-manager \
  iam.gke.io/gcp-service-account=cert-manager@PROJECT_ID.iam.gserviceaccount.com
```

### Azure AKS

```bash
# Use Azure AD workload identity
az identity create --name cert-manager --resource-group your-rg

az role assignment create \
  --assignee <identity-client-id> \
  --role "DNS Zone Contributor" \
  --scope /subscriptions/<subscription-id>/resourceGroups/your-rg
```

## Next Steps

1. **Task 267:** Configure autoscaling (HPA) for API services
2. **Task 268:** Set up monitoring (Prometheus) for metrics collection
3. **Task 269:** Set up logging (Loki/ELK) for centralized logs

## Resources

- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [ACME Protocol](https://tools.ietf.org/html/rfc8555)
- [Certificate Transparency](https://certificate.transparency.dev/)

## Support

For issues related to NeuroLake TLS/SSL:
- GitHub: https://github.com/neurolake/neurolake/issues
- Email: team@neurolake.dev
