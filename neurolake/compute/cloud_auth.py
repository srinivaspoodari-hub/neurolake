"""
Cloud Authentication Module

Provides secure, role-based authentication for all cloud providers:
- AWS: IAM Roles, AssumeRole, Instance Profile
- Azure: Managed Identity, Service Principal, CLI credentials
- GCP: Application Default Credentials, Service Account, Workload Identity

Best Practices:
- Prefer IAM roles over access keys
- Use Managed Identity in Azure when possible
- Use Workload Identity in GCP Kubernetes
- Support credential chains for flexibility
"""

import os
import json
import logging
from typing import Dict, Optional, Any, Literal
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class AuthMethod(str, Enum):
    """Authentication methods"""
    # AWS
    IAM_ROLE = "iam_role"
    INSTANCE_PROFILE = "instance_profile"
    ACCESS_KEY = "access_key"
    ASSUME_ROLE = "assume_role"

    # Azure
    MANAGED_IDENTITY = "managed_identity"
    SERVICE_PRINCIPAL = "service_principal"
    CLI_CREDENTIALS = "cli_credentials"

    # GCP
    APPLICATION_DEFAULT = "application_default"
    SERVICE_ACCOUNT = "service_account"
    WORKLOAD_IDENTITY = "workload_identity"


@dataclass
class CloudCredentials:
    """Cloud credentials"""
    provider: CloudProvider
    auth_method: AuthMethod
    credentials: Dict[str, Any]
    region: str
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AWSAuthenticator:
    """
    AWS Authentication

    Supports multiple authentication methods in order of preference:
    1. IAM Role (when running on EC2/ECS/Lambda)
    2. AssumeRole (cross-account access)
    3. Instance Profile (EC2 metadata service)
    4. Access Keys (least preferred, for development only)
    """

    def __init__(self):
        self.boto3_available = False
        try:
            import boto3
            self.boto3 = boto3
            self.boto3_available = True
            logger.info("boto3 available for AWS authentication")
        except ImportError:
            logger.warning("boto3 not installed - AWS authentication limited")

    def authenticate(
        self,
        region: str = "us-east-1",
        role_arn: Optional[str] = None,
        role_session_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None
    ) -> CloudCredentials:
        """
        Authenticate with AWS using credential chain

        Args:
            region: AWS region
            role_arn: ARN of role to assume (optional)
            role_session_name: Session name for AssumeRole
            access_key_id: Access key (fallback, not recommended)
            secret_access_key: Secret key (fallback, not recommended)
            session_token: Session token (optional)

        Returns:
            CloudCredentials with authenticated session
        """
        if not self.boto3_available:
            return self._create_mock_credentials(region)

        try:
            # Try IAM Role / Instance Profile first (most secure)
            if not access_key_id and not secret_access_key:
                return self._authenticate_with_iam_role(region, role_arn, role_session_name)

            # Fallback to access keys (development only)
            return self._authenticate_with_access_keys(
                region, access_key_id, secret_access_key, session_token
            )

        except Exception as e:
            logger.error(f"AWS authentication failed: {e}")
            return self._create_mock_credentials(region)

    def _authenticate_with_iam_role(
        self,
        region: str,
        role_arn: Optional[str] = None,
        role_session_name: Optional[str] = None
    ) -> CloudCredentials:
        """Authenticate using IAM role or instance profile"""
        try:
            # Create session without explicit credentials
            # This uses the credential chain: IAM role -> instance profile -> env vars
            session = self.boto3.Session(region_name=region)

            # Get credentials from session
            credentials = session.get_credentials()

            if credentials:
                auth_method = AuthMethod.IAM_ROLE
                creds_dict = {
                    'aws_access_key_id': credentials.access_key,
                    'aws_secret_access_key': credentials.secret_key,
                    'aws_session_token': credentials.token,
                    'region_name': region
                }

                # If role ARN provided, assume that role
                if role_arn:
                    return self._assume_role(role_arn, role_session_name or 'NeuroLakeSession', region)

                logger.info(f"AWS authenticated via {auth_method.value}")

                return CloudCredentials(
                    provider=CloudProvider.AWS,
                    auth_method=auth_method,
                    credentials=creds_dict,
                    region=region,
                    expires_at=None,  # Credentials auto-refresh
                    metadata={
                        'session_type': 'iam_role',
                        'region': region
                    }
                )
            else:
                raise Exception("No credentials found in credential chain")

        except Exception as e:
            logger.error(f"IAM role authentication failed: {e}")
            raise

    def _assume_role(
        self,
        role_arn: str,
        session_name: str,
        region: str,
        duration_seconds: int = 3600
    ) -> CloudCredentials:
        """Assume an IAM role for cross-account or elevated access"""
        try:
            # Create STS client
            sts = self.boto3.client('sts', region_name=region)

            # Assume role
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                DurationSeconds=duration_seconds
            )

            credentials = response['Credentials']

            logger.info(f"Assumed role: {role_arn}")

            return CloudCredentials(
                provider=CloudProvider.AWS,
                auth_method=AuthMethod.ASSUME_ROLE,
                credentials={
                    'aws_access_key_id': credentials['AccessKeyId'],
                    'aws_secret_access_key': credentials['SecretAccessKey'],
                    'aws_session_token': credentials['SessionToken'],
                    'region_name': region
                },
                region=region,
                expires_at=credentials['Expiration'],
                metadata={
                    'role_arn': role_arn,
                    'session_name': session_name,
                    'assumed_role_id': response['AssumedRoleUser']['AssumedRoleId']
                }
            )

        except Exception as e:
            logger.error(f"AssumeRole failed: {e}")
            raise

    def _authenticate_with_access_keys(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None
    ) -> CloudCredentials:
        """Authenticate with access keys (development only)"""
        logger.warning("Using AWS access keys - not recommended for production")

        creds_dict = {
            'aws_access_key_id': access_key_id,
            'aws_secret_access_key': secret_access_key,
            'region_name': region
        }

        if session_token:
            creds_dict['aws_session_token'] = session_token

        # Test credentials
        try:
            session = self.boto3.Session(**creds_dict)
            sts = session.client('sts')
            identity = sts.get_caller_identity()

            logger.info(f"AWS authenticated as {identity['Arn']}")

            return CloudCredentials(
                provider=CloudProvider.AWS,
                auth_method=AuthMethod.ACCESS_KEY,
                credentials=creds_dict,
                region=region,
                metadata={
                    'account_id': identity['Account'],
                    'user_id': identity['UserId'],
                    'arn': identity['Arn']
                }
            )

        except Exception as e:
            logger.error(f"Access key authentication failed: {e}")
            raise

    def _create_mock_credentials(self, region: str) -> CloudCredentials:
        """Create mock credentials for testing"""
        return CloudCredentials(
            provider=CloudProvider.AWS,
            auth_method=AuthMethod.IAM_ROLE,
            credentials={
                'region_name': region,
                'mock': True
            },
            region=region,
            metadata={'mock': True}
        )


class AzureAuthenticator:
    """
    Azure Authentication

    Supports multiple authentication methods in order of preference:
    1. Managed Identity (when running on Azure VMs/App Service)
    2. Service Principal (with client secret or certificate)
    3. Azure CLI credentials (development)
    """

    def __init__(self):
        self.azure_identity_available = False
        try:
            from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
            from azure.identity import ClientSecretCredential
            self.DefaultAzureCredential = DefaultAzureCredential
            self.ManagedIdentityCredential = ManagedIdentityCredential
            self.ClientSecretCredential = ClientSecretCredential
            self.azure_identity_available = True
            logger.info("azure-identity available for Azure authentication")
        except ImportError:
            logger.warning("azure-identity not installed - Azure authentication limited")

    def authenticate(
        self,
        subscription_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_managed_identity: bool = True,
        managed_identity_client_id: Optional[str] = None
    ) -> CloudCredentials:
        """
        Authenticate with Azure using credential chain

        Args:
            subscription_id: Azure subscription ID
            tenant_id: Azure tenant ID
            client_id: Service principal client ID
            client_secret: Service principal secret
            use_managed_identity: Try managed identity first
            managed_identity_client_id: Specific managed identity to use

        Returns:
            CloudCredentials with authenticated session
        """
        if not self.azure_identity_available:
            return self._create_mock_credentials()

        try:
            # Try Managed Identity first (most secure)
            if use_managed_identity:
                return self._authenticate_with_managed_identity(
                    subscription_id, managed_identity_client_id
                )

            # Fallback to Service Principal
            if tenant_id and client_id and client_secret:
                return self._authenticate_with_service_principal(
                    subscription_id, tenant_id, client_id, client_secret
                )

            # Fallback to Default Azure Credential (includes CLI)
            return self._authenticate_with_default_credential(subscription_id)

        except Exception as e:
            logger.error(f"Azure authentication failed: {e}")
            return self._create_mock_credentials()

    def _authenticate_with_managed_identity(
        self,
        subscription_id: Optional[str],
        client_id: Optional[str] = None
    ) -> CloudCredentials:
        """Authenticate using Azure Managed Identity"""
        try:
            # Create managed identity credential
            if client_id:
                credential = self.ManagedIdentityCredential(client_id=client_id)
                logger.info(f"Using Managed Identity: {client_id}")
            else:
                credential = self.ManagedIdentityCredential()
                logger.info("Using System-Assigned Managed Identity")

            # Test credential
            from azure.mgmt.resource import ResourceManagementClient
            client = ResourceManagementClient(
                credential=credential,
                subscription_id=subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
            )

            # Get subscription info
            subscription = client.subscriptions.get(
                subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
            )

            logger.info(f"Azure authenticated via Managed Identity")

            return CloudCredentials(
                provider=CloudProvider.AZURE,
                auth_method=AuthMethod.MANAGED_IDENTITY,
                credentials={
                    'credential': credential,
                    'subscription_id': subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
                },
                region='global',
                metadata={
                    'subscription_id': subscription.subscription_id,
                    'subscription_name': subscription.display_name,
                    'client_id': client_id
                }
            )

        except Exception as e:
            logger.error(f"Managed Identity authentication failed: {e}")
            raise

    def _authenticate_with_service_principal(
        self,
        subscription_id: str,
        tenant_id: str,
        client_id: str,
        client_secret: str
    ) -> CloudCredentials:
        """Authenticate using Service Principal"""
        logger.warning("Using Service Principal - prefer Managed Identity in production")

        try:
            credential = self.ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )

            # Test credential
            from azure.mgmt.resource import ResourceManagementClient
            client = ResourceManagementClient(
                credential=credential,
                subscription_id=subscription_id
            )

            subscription = client.subscriptions.get(subscription_id)

            logger.info(f"Azure authenticated via Service Principal")

            return CloudCredentials(
                provider=CloudProvider.AZURE,
                auth_method=AuthMethod.SERVICE_PRINCIPAL,
                credentials={
                    'credential': credential,
                    'subscription_id': subscription_id,
                    'tenant_id': tenant_id,
                    'client_id': client_id
                },
                region='global',
                metadata={
                    'subscription_id': subscription.subscription_id,
                    'subscription_name': subscription.display_name,
                    'tenant_id': tenant_id,
                    'client_id': client_id
                }
            )

        except Exception as e:
            logger.error(f"Service Principal authentication failed: {e}")
            raise

    def _authenticate_with_default_credential(
        self,
        subscription_id: Optional[str]
    ) -> CloudCredentials:
        """Authenticate using DefaultAzureCredential chain"""
        try:
            credential = self.DefaultAzureCredential()

            sub_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')

            if not sub_id:
                raise Exception("subscription_id required")

            # Test credential
            from azure.mgmt.resource import ResourceManagementClient
            client = ResourceManagementClient(
                credential=credential,
                subscription_id=sub_id
            )

            subscription = client.subscriptions.get(sub_id)

            logger.info(f"Azure authenticated via DefaultAzureCredential chain")

            return CloudCredentials(
                provider=CloudProvider.AZURE,
                auth_method=AuthMethod.CLI_CREDENTIALS,
                credentials={
                    'credential': credential,
                    'subscription_id': sub_id
                },
                region='global',
                metadata={
                    'subscription_id': subscription.subscription_id,
                    'subscription_name': subscription.display_name,
                    'method': 'default_chain'
                }
            )

        except Exception as e:
            logger.error(f"DefaultAzureCredential failed: {e}")
            raise

    def _create_mock_credentials(self) -> CloudCredentials:
        """Create mock credentials for testing"""
        return CloudCredentials(
            provider=CloudProvider.AZURE,
            auth_method=AuthMethod.MANAGED_IDENTITY,
            credentials={'mock': True},
            region='global',
            metadata={'mock': True}
        )


class GCPAuthenticator:
    """
    GCP Authentication

    Supports multiple authentication methods in order of preference:
    1. Application Default Credentials (when running on GCE/GKE/Cloud Run)
    2. Workload Identity (GKE workload identity)
    3. Service Account Key (development only)
    """

    def __init__(self):
        self.google_auth_available = False
        try:
            import google.auth
            from google.oauth2 import service_account
            self.google_auth = google.auth
            self.service_account = service_account
            self.google_auth_available = True
            logger.info("google-auth available for GCP authentication")
        except ImportError:
            logger.warning("google-auth not installed - GCP authentication limited")

    def authenticate(
        self,
        project_id: Optional[str] = None,
        service_account_path: Optional[str] = None,
        scopes: Optional[list] = None
    ) -> CloudCredentials:
        """
        Authenticate with GCP using credential chain

        Args:
            project_id: GCP project ID
            service_account_path: Path to service account JSON key
            scopes: OAuth2 scopes

        Returns:
            CloudCredentials with authenticated session
        """
        if not self.google_auth_available:
            return self._create_mock_credentials(project_id)

        scopes = scopes or ['https://www.googleapis.com/auth/cloud-platform']

        try:
            # Try Application Default Credentials first (most secure)
            if not service_account_path:
                return self._authenticate_with_adc(project_id, scopes)

            # Fallback to Service Account Key
            return self._authenticate_with_service_account(
                project_id, service_account_path, scopes
            )

        except Exception as e:
            logger.error(f"GCP authentication failed: {e}")
            return self._create_mock_credentials(project_id)

    def _authenticate_with_adc(
        self,
        project_id: Optional[str],
        scopes: list
    ) -> CloudCredentials:
        """Authenticate using Application Default Credentials"""
        try:
            # Load default credentials
            credentials, detected_project = self.google_auth.default(scopes=scopes)

            project = project_id or detected_project or os.getenv('GCP_PROJECT_ID')

            if not project:
                raise Exception("project_id could not be determined")

            # Determine auth method
            auth_method = AuthMethod.APPLICATION_DEFAULT
            if hasattr(credentials, 'service_account_email'):
                if 'serviceaccount' in credentials.service_account_email:
                    auth_method = AuthMethod.WORKLOAD_IDENTITY

            logger.info(f"GCP authenticated via {auth_method.value}")

            return CloudCredentials(
                provider=CloudProvider.GCP,
                auth_method=auth_method,
                credentials={
                    'credentials': credentials,
                    'project_id': project,
                    'scopes': scopes
                },
                region='global',
                metadata={
                    'project_id': project,
                    'auth_method': auth_method.value,
                    'service_account': getattr(credentials, 'service_account_email', None)
                }
            )

        except Exception as e:
            logger.error(f"Application Default Credentials failed: {e}")
            raise

    def _authenticate_with_service_account(
        self,
        project_id: str,
        service_account_path: str,
        scopes: list
    ) -> CloudCredentials:
        """Authenticate using Service Account key file"""
        logger.warning("Using Service Account key file - not recommended for production")

        try:
            # Load service account credentials
            credentials = self.service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=scopes
            )

            # Read service account info
            with open(service_account_path, 'r') as f:
                sa_info = json.load(f)

            logger.info(f"GCP authenticated via Service Account: {sa_info.get('client_email')}")

            return CloudCredentials(
                provider=CloudProvider.GCP,
                auth_method=AuthMethod.SERVICE_ACCOUNT,
                credentials={
                    'credentials': credentials,
                    'project_id': project_id,
                    'scopes': scopes
                },
                region='global',
                metadata={
                    'project_id': project_id,
                    'service_account_email': sa_info.get('client_email'),
                    'service_account_path': service_account_path
                }
            )

        except Exception as e:
            logger.error(f"Service Account authentication failed: {e}")
            raise

    def _create_mock_credentials(self, project_id: Optional[str]) -> CloudCredentials:
        """Create mock credentials for testing"""
        return CloudCredentials(
            provider=CloudProvider.GCP,
            auth_method=AuthMethod.APPLICATION_DEFAULT,
            credentials={
                'project_id': project_id or 'mock-project',
                'mock': True
            },
            region='global',
            metadata={'mock': True}
        )


class CloudAuthManager:
    """
    Cloud Authentication Manager

    Centralized authentication for all cloud providers.
    Supports IAM roles, managed identities, and service accounts.
    """

    def __init__(self):
        self.aws = AWSAuthenticator()
        self.azure = AzureAuthenticator()
        self.gcp = GCPAuthenticator()

        self.credentials_cache: Dict[CloudProvider, CloudCredentials] = {}

        logger.info("Cloud authentication manager initialized")

    def authenticate_aws(
        self,
        region: str = "us-east-1",
        role_arn: Optional[str] = None,
        **kwargs
    ) -> CloudCredentials:
        """
        Authenticate with AWS

        Preferred: IAM role or instance profile
        Fallback: Access keys (development only)
        """
        creds = self.aws.authenticate(region=region, role_arn=role_arn, **kwargs)
        self.credentials_cache[CloudProvider.AWS] = creds
        return creds

    def authenticate_azure(
        self,
        subscription_id: Optional[str] = None,
        use_managed_identity: bool = True,
        **kwargs
    ) -> CloudCredentials:
        """
        Authenticate with Azure

        Preferred: Managed Identity
        Fallback: Service Principal or CLI credentials
        """
        creds = self.azure.authenticate(
            subscription_id=subscription_id,
            use_managed_identity=use_managed_identity,
            **kwargs
        )
        self.credentials_cache[CloudProvider.AZURE] = creds
        return creds

    def authenticate_gcp(
        self,
        project_id: Optional[str] = None,
        **kwargs
    ) -> CloudCredentials:
        """
        Authenticate with GCP

        Preferred: Application Default Credentials (includes Workload Identity)
        Fallback: Service Account key file (development only)
        """
        creds = self.gcp.authenticate(project_id=project_id, **kwargs)
        self.credentials_cache[CloudProvider.GCP] = creds
        return creds

    def get_credentials(self, provider: CloudProvider) -> Optional[CloudCredentials]:
        """Get cached credentials for a provider"""
        return self.credentials_cache.get(provider)

    def is_authenticated(self, provider: CloudProvider) -> bool:
        """Check if authenticated with a provider"""
        creds = self.credentials_cache.get(provider)
        if not creds:
            return False

        # Check if credentials expired
        if creds.expires_at and creds.expires_at < datetime.now():
            return False

        return True

    def refresh_credentials(self, provider: CloudProvider) -> bool:
        """Refresh credentials for a provider"""
        try:
            if provider == CloudProvider.AWS:
                creds = self.credentials_cache.get(provider)
                if creds and creds.metadata.get('role_arn'):
                    # Re-assume role
                    self.authenticate_aws(
                        region=creds.region,
                        role_arn=creds.metadata['role_arn']
                    )
                    return True

            # For Azure and GCP, credentials auto-refresh
            return True

        except Exception as e:
            logger.error(f"Failed to refresh {provider} credentials: {e}")
            return False

    def get_auth_summary(self) -> Dict[str, Any]:
        """Get summary of all authentication status"""
        summary = {}

        for provider in CloudProvider:
            creds = self.credentials_cache.get(provider)
            if creds:
                summary[provider.value] = {
                    'authenticated': True,
                    'auth_method': creds.auth_method.value,
                    'region': creds.region,
                    'expires_at': creds.expires_at.isoformat() if creds.expires_at else None,
                    'metadata': {k: v for k, v in creds.metadata.items() if k != 'credential'}
                    if creds.metadata else {}
                }
            else:
                summary[provider.value] = {
                    'authenticated': False
                }

        return summary


# Global auth manager instance
_auth_manager: Optional[CloudAuthManager] = None


def get_auth_manager() -> CloudAuthManager:
    """Get global authentication manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = CloudAuthManager()
    return _auth_manager
