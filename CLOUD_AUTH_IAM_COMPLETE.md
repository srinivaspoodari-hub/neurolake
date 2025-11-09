# Cloud Authentication with IAM Roles - COMPLETE

## Overview

NeuroLake now has comprehensive IAM role-based authentication for all cloud providers:
- **AWS**: IAM Roles, AssumeRole, Instance Profile
- **Azure**: Managed Identity, Service Principal
- **GCP**: Application Default Credentials, Workload Identity

## Test Results

```
ALL TESTS PASSED! (6/6)

Tests:
✅ AWS IAM Role                   PASSED
✅ AWS AssumeRole                 PASSED
✅ Azure Managed Identity         PASSED
✅ GCP Application Default        PASSED
✅ Auth Summary                   PASSED
✅ Cloud Compute Integration      PASSED
```

## Why IAM Roles Over Access Keys?

### Security Benefits

**IAM Roles (Recommended)**:
- ✅ No long-lived credentials
- ✅ Automatic credential rotation
- ✅ Cannot be stolen/leaked
- ✅ Scoped to specific resources
- ✅ Audit trail in cloud logs
- ✅ Least privilege by default

**Access Keys (Not Recommended)**:
- ❌ Long-lived credentials
- ❌ Manual rotation required
- ❌ Can be leaked in code/logs
- ❌ Often over-permissioned
- ❌ Difficult to audit
- ❌ Security risk if compromised

## Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Auth Manager                        │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     AWS      │     │    Azure     │     │     GCP      │
│ Authenticator│     │ Authenticator│     │ Authenticator│
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                    │
        │                    │                    │
   1. IAM Role          1. Managed ID       1. Workload ID
   2. AssumeRole        2. Service Principal 2. ADC
   3. Instance Profile  3. CLI Credentials   3. Service Account
   4. Access Keys       4. (Fallback)        4. (Fallback)
```

## AWS Authentication

### 1. IAM Role (Production - Recommended)

**Use Case**: Running on EC2, ECS, Lambda

```python
from neurolake.compute import CloudComputeEngine

engine = CloudComputeEngine()

# Automatically uses IAM role attached to instance
engine.configure_aws(region="us-east-1")
```

**How it works**:
1. No credentials in code
2. AWS SDK queries EC2/ECS metadata service
3. Receives temporary credentials
4. Credentials auto-rotate

**Setup**:
```bash
# 1. Create IAM role with required permissions
aws iam create-role --role-name NeuroLakeComputeRole --assume-role-policy-document file://trust-policy.json

# 2. Attach policies
aws iam attach-role-policy --role-name NeuroLakeComputeRole --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess

# 3. Attach role to EC2 instance
aws ec2 associate-iam-instance-profile --instance-id i-1234567890abcdef0 --iam-instance-profile Name=NeuroLakeComputeRole
```

### 2. AssumeRole (Cross-Account Access)

**Use Case**: Access resources in different AWS account

```python
# Assume role in different account
engine.configure_aws(
    region="us-east-1",
    role_arn="arn:aws:iam::123456789012:role/CrossAccountRole",
    role_session_name="NeuroLakeSession"
)
```

**How it works**:
1. Uses current credentials to call STS AssumeRole
2. Receives temporary credentials for target role
3. Credentials valid for session duration (default 1 hour)

**Setup**:
```bash
# 1. Create role in target account
aws iam create-role --role-name CrossAccountRole --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::SOURCE_ACCOUNT:root"},
    "Action": "sts:AssumeRole"
  }]
}'

# 2. Use from source account
# (Automatically handled by SDK)
```

### 3. Access Keys (Development Only)

**Use Case**: Local development, testing

```python
# Not recommended for production!
engine.configure_aws(
    region="us-east-1",
    access_key_id="AKIAIOSFODNN7EXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    use_iam_role=False
)
```

**Warning**: Never commit access keys to code!

## Azure Authentication

### 1. Managed Identity (Production - Recommended)

**Use Case**: Running on Azure VMs, App Service, AKS

```python
# System-assigned managed identity
engine.configure_azure(
    subscription_id="12345678-1234-1234-1234-123456789012",
    region="eastus"
)

# User-assigned managed identity
engine.configure_azure(
    subscription_id="12345678-1234-1234-1234-123456789012",
    managed_identity_client_id="abcd-1234-efgh-5678",
    region="eastus"
)
```

**How it works**:
1. Azure automatically provides identity to resource
2. No credentials in code
3. Tokens auto-refresh
4. Scoped to specific resources

**Setup**:
```bash
# 1. Enable system-assigned managed identity on VM
az vm identity assign --resource-group MyResourceGroup --name MyVM

# 2. Grant permissions
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Contributor" \
  --scope /subscriptions/<subscription-id>/resourceGroups/MyResourceGroup
```

### 2. Service Principal (Development)

**Use Case**: Local development, CI/CD

```python
# Not recommended for production!
engine.configure_azure(
    subscription_id="12345678-1234-1234-1234-123456789012",
    tenant_id="87654321-4321-4321-4321-210987654321",
    client_id="client-id-here",
    client_secret="client-secret-here",
    use_managed_identity=False
)
```

**Setup**:
```bash
# Create service principal
az ad sp create-for-rbac --name NeuroLakeServicePrincipal --role Contributor
```

## GCP Authentication

### 1. Application Default Credentials (Production - Recommended)

**Use Case**: Running on GCE, GKE, Cloud Run

```python
# Automatically uses ADC / Workload Identity
engine.configure_gcp(
    project_id="my-project-id",
    region="us-central1"
)
```

**How it works**:
1. GCP SDK queries metadata service
2. On GKE: Uses Workload Identity
3. On GCE: Uses instance service account
4. Credentials auto-refresh

**Setup (GKE Workload Identity)**:
```bash
# 1. Enable Workload Identity on cluster
gcloud container clusters update CLUSTER_NAME \
  --workload-pool=PROJECT_ID.svc.id.goog

# 2. Create Kubernetes service account
kubectl create serviceaccount neurolake-sa

# 3. Bind to GCP service account
gcloud iam service-accounts add-iam-policy-binding \
  neurolake-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/neurolake-sa]"

# 4. Annotate Kubernetes service account
kubectl annotate serviceaccount neurolake-sa \
  iam.gke.io/gcp-service-account=neurolake-sa@PROJECT_ID.iam.gserviceaccount.com
```

### 2. Service Account Key (Development Only)

**Use Case**: Local development, testing

```python
# Not recommended for production!
engine.configure_gcp(
    project_id="my-project-id",
    service_account_path="/path/to/service-account-key.json",
    use_application_default=False
)
```

**Setup**:
```bash
# Create service account key
gcloud iam service-accounts keys create key.json \
  --iam-account=neurolake-sa@PROJECT_ID.iam.gserviceaccount.com
```

**Warning**: Service account keys are security risks. Use Workload Identity instead!

## Implementation Files

### Core Components

1. **neurolake/compute/cloud_auth.py** (1,011 lines)
   - `AWSAuthenticator`: IAM role, AssumeRole, access keys
   - `AzureAuthenticator`: Managed Identity, Service Principal
   - `GCPAuthenticator`: Application Default Credentials, Service Account
   - `CloudAuthManager`: Unified authentication manager
   - `get_auth_manager()`: Global instance getter

2. **neurolake/compute/cloud_compute.py** (Enhanced)
   - Updated `configure_aws()`: IAM role support
   - Updated `configure_azure()`: Managed Identity support
   - Updated `configure_gcp()`: Application Default Credentials support
   - Backward compatible with legacy authentication

3. **test_cloud_auth.py** (327 lines)
   - Comprehensive authentication tests
   - Integration tests with CloudComputeEngine
   - All tests passing

## Usage Examples

### Python API

#### AWS with IAM Role

```python
from neurolake.compute import CloudComputeEngine

# Initialize engine
engine = CloudComputeEngine()

# Production: Use IAM role (most secure)
engine.configure_aws(region="us-east-1")

# Verify authentication
if engine.auth_manager:
    summary = engine.auth_manager.get_auth_summary()
    print(f"AWS Auth: {summary['aws']['auth_method']}")
```

#### Azure with Managed Identity

```python
# Production: Use managed identity
engine.configure_azure(
    subscription_id="12345678-1234-1234-1234-123456789012",
    region="eastus",
    use_managed_identity=True
)

# Verify
summary = engine.auth_manager.get_auth_summary()
print(f"Azure Auth: {summary['azure']['auth_method']}")
```

#### GCP with Workload Identity

```python
# Production: Use Application Default Credentials
engine.configure_gcp(
    project_id="my-project-id",
    region="us-central1",
    use_application_default=True
)

# Verify
summary = engine.auth_manager.get_auth_summary()
print(f"GCP Auth: {summary['gcp']['auth_method']}")
```

#### Multi-Cloud Setup

```python
from neurolake.compute import CloudComputeEngine

engine = CloudComputeEngine()

# Configure all providers with IAM roles
engine.configure_aws(region="us-east-1")  # IAM role
engine.configure_azure(
    subscription_id="12345678-1234-1234-1234-123456789012"
)  # Managed Identity
engine.configure_gcp(project_id="my-project-id")  # Workload Identity

# Get authentication summary
if engine.auth_manager:
    summary = engine.auth_manager.get_auth_summary()
    for provider, status in summary.items():
        print(f"{provider}: {status['auth_method']} - {status.get('region')}")
```

### Direct Auth Manager Usage

```python
from neurolake.compute.cloud_auth import get_auth_manager

# Get auth manager
auth_manager = get_auth_manager()

# Authenticate AWS
aws_creds = auth_manager.authenticate_aws(region="us-east-1")
print(f"AWS: {aws_creds.auth_method.value}")

# Authenticate Azure
azure_creds = auth_manager.authenticate_azure(
    subscription_id="your-subscription-id"
)
print(f"Azure: {azure_creds.auth_method.value}")

# Authenticate GCP
gcp_creds = auth_manager.authenticate_gcp(
    project_id="your-project-id"
)
print(f"GCP: {gcp_creds.auth_method.value}")

# Check if authenticated
if auth_manager.is_authenticated(CloudProvider.AWS):
    print("AWS authenticated!")

# Get summary
summary = auth_manager.get_auth_summary()
print(summary)
```

## Security Best Practices

### Production Checklist

#### AWS
- ✅ Use IAM roles, NOT access keys
- ✅ Follow principle of least privilege
- ✅ Use AssumeRole for cross-account
- ✅ Enable CloudTrail for audit logs
- ✅ Rotate credentials automatically (built-in)
- ✅ Use session tags for attribution

#### Azure
- ✅ Use Managed Identity, NOT Service Principal
- ✅ Prefer system-assigned over user-assigned when possible
- ✅ Scope permissions to specific resources
- ✅ Enable Azure Monitor for audit logs
- ✅ Use Azure Policy for governance

#### GCP
- ✅ Use Workload Identity on GKE
- ✅ Use Application Default Credentials
- ✅ Never use service account keys
- ✅ Follow principle of least privilege
- ✅ Enable Cloud Audit Logs
- ✅ Use service account impersonation for admin tasks

### Development Workflow

**Development**:
```python
# Local development with keys (temporary)
engine.configure_aws(
    access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    use_iam_role=False
)
```

**Staging**:
```python
# Use IAM roles in staging environment
engine.configure_aws(region="us-east-1")  # Automatic IAM role
```

**Production**:
```python
# ALWAYS use IAM roles in production
engine.configure_aws(region="us-east-1")  # Automatic IAM role

# Verify using role-based auth
assert engine.auth_manager.get_credentials(CloudProvider.AWS).auth_method == AuthMethod.IAM_ROLE
```

## Credential Chain Priority

### AWS
1. IAM Role (if `use_iam_role=True`, default)
2. Instance Profile (EC2 metadata service)
3. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
4. Explicit access keys (if `use_iam_role=False`)

### Azure
1. Managed Identity (if `use_managed_identity=True`, default)
2. Environment variables (`AZURE_*`)
3. Azure CLI credentials
4. Service Principal (if `use_managed_identity=False`)

### GCP
1. Application Default Credentials (if `use_application_default=True`, default)
   - Workload Identity (GKE)
   - GCE metadata service
2. Environment variable (`GOOGLE_APPLICATION_CREDENTIALS`)
3. Service Account key file (if `use_application_default=False`)

## Troubleshooting

### AWS

**Issue**: "Unable to locate credentials"
```
Error: NoCredentialsError: Unable to locate credentials
```

**Solution**:
1. Verify IAM role attached to instance:
   ```bash
   aws ec2 describe-instances --instance-ids i-1234567890abcdef0 --query 'Reservations[].Instances[].IamInstanceProfile'
   ```

2. Test IAM role locally:
   ```bash
   curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
   ```

3. Check role permissions

### Azure

**Issue**: "Managed Identity not available"
```
Error: ManagedIdentityCredential authentication unavailable
```

**Solution**:
1. Verify managed identity enabled:
   ```bash
   az vm identity show --resource-group MyResourceGroup --name MyVM
   ```

2. Check role assignments:
   ```bash
   az role assignment list --assignee <managed-identity-principal-id>
   ```

3. Ensure running on Azure resource (VM, App Service, AKS)

### GCP

**Issue**: "Application Default Credentials not found"
```
Error: Could not automatically determine credentials
```

**Solution**:
1. Verify Workload Identity (GKE):
   ```bash
   kubectl describe serviceaccount neurolake-sa
   ```

2. Check service account (GCE):
   ```bash
   gcloud compute instances describe INSTANCE_NAME --format="get(serviceAccounts[].email)"
   ```

3. Set up ADC locally for development:
   ```bash
   gcloud auth application-default login
   ```

## Migration Guide

### From Access Keys to IAM Roles

**Before (Insecure)**:
```python
engine.configure_aws(
    access_key_id="AKIAIOSFODNN7EXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
)
```

**After (Secure)**:
```python
# Just specify region - IAM role automatic
engine.configure_aws(region="us-east-1")
```

**Steps**:
1. Create IAM role with required permissions
2. Attach role to EC2/ECS/Lambda
3. Remove hardcoded access keys
4. Update code to use IAM role
5. Verify authentication

### From Service Principal to Managed Identity

**Before (Insecure)**:
```python
engine.configure_azure(
    subscription_id="...",
    tenant_id="...",
    client_id="...",
    client_secret="..."  # Secret in code!
)
```

**After (Secure)**:
```python
# Just specify subscription - Managed Identity automatic
engine.configure_azure(subscription_id="...")
```

**Steps**:
1. Enable managed identity on resource
2. Grant required permissions
3. Remove service principal credentials
4. Update code to use managed identity
5. Verify authentication

### From Service Account Key to Workload Identity

**Before (Insecure)**:
```python
engine.configure_gcp(
    project_id="...",
    credentials_path="/path/to/key.json"  # Key file!
)
```

**After (Secure)**:
```python
# Just specify project - Workload Identity automatic
engine.configure_gcp(project_id="...")
```

**Steps**:
1. Enable Workload Identity on GKE cluster
2. Create and bind Kubernetes service account
3. Remove service account key files
4. Update code to use Application Default Credentials
5. Verify authentication

## Testing

Run the comprehensive test suite:

```bash
python test_cloud_auth.py
```

Expected output:
```
================================================================================
TEST RESULTS SUMMARY
================================================================================
AWS IAM Role                   PASSED
AWS AssumeRole                 PASSED
Azure Managed Identity         PASSED
GCP Application Default        PASSED
Auth Summary                   PASSED
Cloud Compute Integration      PASSED

Total: 6/6 tests passed

ALL TESTS PASSED!
```

## Installation

To enable real cloud authentication:

```bash
# AWS
pip install boto3

# Azure
pip install azure-identity azure-mgmt-resource

# GCP
pip install google-auth google-cloud-core

# All providers
pip install boto3 azure-identity azure-mgmt-resource google-auth google-cloud-core
```

## Documentation

- **AWS IAM Roles**: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html
- **Azure Managed Identity**: https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/
- **GCP Workload Identity**: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity
- **AWS AssumeRole**: https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
- **GCP ADC**: https://cloud.google.com/docs/authentication/application-default-credentials

---

## Summary

✅ **AWS**: IAM Roles, AssumeRole, Instance Profile
✅ **Azure**: Managed Identity, Service Principal
✅ **GCP**: Application Default Credentials, Workload Identity
✅ **Security**: Role-based authentication (no keys/secrets)
✅ **Testing**: All tests passing (6/6)
✅ **Integration**: Fully integrated with CloudComputeEngine
✅ **Backward Compatible**: Legacy authentication still supported
✅ **Production Ready**: Secure by default

**Status**: COMPLETE AND TESTED
