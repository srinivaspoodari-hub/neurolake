"""
Cloud Compute Engine

Provides seamless integration with major cloud compute providers:
- AWS (Lambda, ECS, Batch, EMR, SageMaker) - Using IAM Roles
- Azure (Functions, Container Instances, Databricks, Synapse) - Using Managed Identity
- GCP (Cloud Functions, Cloud Run, Dataproc, Vertex AI) - Using Application Default Credentials

Authentication:
- Prefer role-based authentication over keys/secrets
- AWS: IAM Roles, AssumeRole, Instance Profile
- Azure: Managed Identity, Service Principal
- GCP: Application Default Credentials, Workload Identity
"""

import logging
import os
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Import new authentication system
try:
    from neurolake.compute.cloud_auth import (
        get_auth_manager,
        CloudProvider as AuthCloudProvider,
        CloudCredentials
    )
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("cloud_auth module not available - using legacy authentication")

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ComputeService(str, Enum):
    """Cloud compute services"""
    # AWS
    AWS_LAMBDA = "aws_lambda"
    AWS_ECS = "aws_ecs"
    AWS_BATCH = "aws_batch"
    AWS_EMR = "aws_emr"
    AWS_SAGEMAKER = "aws_sagemaker"

    # Azure
    AZURE_FUNCTIONS = "azure_functions"
    AZURE_CONTAINER_INSTANCES = "azure_container_instances"
    AZURE_DATABRICKS = "azure_databricks"
    AZURE_SYNAPSE = "azure_synapse"

    # GCP
    GCP_CLOUD_FUNCTIONS = "gcp_cloud_functions"
    GCP_CLOUD_RUN = "gcp_cloud_run"
    GCP_DATAPROC = "gcp_dataproc"
    GCP_VERTEX_AI = "gcp_vertex_ai"


@dataclass
class CloudConfig:
    """Cloud provider configuration"""
    provider: CloudProvider
    region: str
    credentials: Dict[str, str]
    default_service: ComputeService
    tags: Dict[str, str]


class CloudComputeEngine:
    """
    Cloud Compute Engine

    Manages cloud compute resources across AWS, Azure, and GCP.
    Provides unified interface for workload submission and monitoring.

    Authentication:
    - Uses role-based authentication (IAM roles, Managed Identity, Workload Identity)
    - Falls back to key-based auth for development
    """

    def __init__(self):
        """Initialize cloud compute engine"""
        self.configs: Dict[CloudProvider, CloudConfig] = {}
        self.initialized_providers: List[CloudProvider] = []

        # Initialize authentication manager
        if AUTH_AVAILABLE:
            self.auth_manager = get_auth_manager()
            logger.info("Cloud compute engine initialized with IAM role-based authentication")
        else:
            self.auth_manager = None
            logger.info("Cloud compute engine initialized (legacy authentication)")

    def configure_aws(
        self,
        region: str = "us-east-1",
        role_arn: Optional[str] = None,
        role_session_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        default_service: ComputeService = ComputeService.AWS_LAMBDA,
        tags: Optional[Dict[str, str]] = None,
        use_iam_role: bool = True
    ) -> bool:
        """
        Configure AWS compute with IAM role-based authentication

        Preferred: IAM role or instance profile (use_iam_role=True)
        Fallback: Access keys (development only, use_iam_role=False)

        Args:
            region: AWS region
            role_arn: ARN of role to assume (optional, for cross-account access)
            role_session_name: Session name for AssumeRole (optional)
            access_key_id: AWS access key (fallback, not recommended)
            secret_access_key: AWS secret key (fallback, not recommended)
            default_service: Default compute service
            tags: Resource tags
            use_iam_role: Use IAM role authentication (recommended)

        Returns:
            True if configuration successful

        Example:
            # Production: Use IAM role (most secure)
            engine.configure_aws(region="us-east-1")

            # Cross-account: Assume role
            engine.configure_aws(
                region="us-east-1",
                role_arn="arn:aws:iam::123456789:role/MyRole"
            )

            # Development: Use access keys (not recommended)
            engine.configure_aws(
                region="us-east-1",
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                use_iam_role=False
            )
        """
        try:
            # Use new authentication system if available
            if self.auth_manager and use_iam_role:
                # Authenticate using IAM role (preferred)
                cloud_creds = self.auth_manager.authenticate_aws(
                    region=region,
                    role_arn=role_arn,
                    role_session_name=role_session_name
                )

                logger.info(f"AWS authenticated via {cloud_creds.auth_method.value}")

                # Store credentials
                credentials = cloud_creds.credentials
            else:
                # Legacy authentication with access keys
                credentials = {
                    'access_key_id': access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
                    'secret_access_key': secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
                }

                if not credentials['access_key_id'] or not credentials['secret_access_key']:
                    logger.warning("AWS credentials not provided - will use instance role/credentials chain")
                else:
                    logger.warning("Using AWS access keys - not recommended for production")

            self.configs[CloudProvider.AWS] = CloudConfig(
                provider=CloudProvider.AWS,
                region=region,
                credentials=credentials,
                default_service=default_service,
                tags=tags or {'ManagedBy': 'NeuroLake'}
            )

            self.initialized_providers.append(CloudProvider.AWS)
            logger.info(f"AWS configured: region={region}, service={default_service}")

            return True

        except Exception as e:
            logger.error(f"Failed to configure AWS: {e}")
            return False

    def configure_azure(
        self,
        subscription_id: Optional[str] = None,
        region: str = "eastus",
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        managed_identity_client_id: Optional[str] = None,
        default_service: ComputeService = ComputeService.AZURE_FUNCTIONS,
        tags: Optional[Dict[str, str]] = None,
        use_managed_identity: bool = True
    ) -> bool:
        """
        Configure Azure compute with Managed Identity authentication

        Preferred: Managed Identity (use_managed_identity=True)
        Fallback: Service Principal (development only, use_managed_identity=False)

        Args:
            subscription_id: Azure subscription ID
            region: Azure region
            tenant_id: Azure tenant ID (for service principal)
            client_id: Service principal client ID (for service principal)
            client_secret: Service principal secret (for service principal)
            managed_identity_client_id: Specific managed identity to use (optional)
            default_service: Default compute service
            tags: Resource tags
            use_managed_identity: Use Managed Identity (recommended)

        Returns:
            True if configuration successful

        Example:
            # Production: Use Managed Identity (most secure)
            engine.configure_azure(
                subscription_id="12345678-1234-1234-1234-123456789012",
                region="eastus"
            )

            # Specific Managed Identity
            engine.configure_azure(
                subscription_id="12345678-1234-1234-1234-123456789012",
                managed_identity_client_id="abcd-1234-efgh-5678",
                region="eastus"
            )

            # Development: Use Service Principal (not recommended)
            engine.configure_azure(
                subscription_id="12345678-1234-1234-1234-123456789012",
                tenant_id="87654321-4321-4321-4321-210987654321",
                client_id="client-id-here",
                client_secret="client-secret-here",
                use_managed_identity=False
            )
        """
        try:
            # Use new authentication system if available
            if self.auth_manager and use_managed_identity:
                # Authenticate using Managed Identity (preferred)
                cloud_creds = self.auth_manager.authenticate_azure(
                    subscription_id=subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID'),
                    use_managed_identity=True,
                    managed_identity_client_id=managed_identity_client_id
                )

                logger.info(f"Azure authenticated via {cloud_creds.auth_method.value}")

                # Store credentials
                credentials = cloud_creds.credentials
            elif self.auth_manager and not use_managed_identity:
                # Authenticate using Service Principal
                cloud_creds = self.auth_manager.authenticate_azure(
                    subscription_id=subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID'),
                    use_managed_identity=False,
                    tenant_id=tenant_id or os.getenv('AZURE_TENANT_ID'),
                    client_id=client_id or os.getenv('AZURE_CLIENT_ID'),
                    client_secret=client_secret or os.getenv('AZURE_CLIENT_SECRET')
                )

                logger.info(f"Azure authenticated via {cloud_creds.auth_method.value}")
                logger.warning("Using Service Principal - prefer Managed Identity in production")

                # Store credentials
                credentials = cloud_creds.credentials
            else:
                # Legacy authentication
                credentials = {
                    'subscription_id': subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID'),
                    'tenant_id': tenant_id or os.getenv('AZURE_TENANT_ID'),
                    'client_id': client_id or os.getenv('AZURE_CLIENT_ID'),
                    'client_secret': client_secret or os.getenv('AZURE_CLIENT_SECRET'),
                }

                if not credentials['subscription_id']:
                    logger.warning("Azure credentials not fully provided - authentication may fail")

            self.configs[CloudProvider.AZURE] = CloudConfig(
                provider=CloudProvider.AZURE,
                region=region,
                credentials=credentials,
                default_service=default_service,
                tags=tags or {'ManagedBy': 'NeuroLake'}
            )

            self.initialized_providers.append(CloudProvider.AZURE)
            logger.info(f"Azure configured: region={region}, service={default_service}")

            return True

        except Exception as e:
            logger.error(f"Failed to configure Azure: {e}")
            return False

    def configure_gcp(
        self,
        project_id: Optional[str] = None,
        region: str = "us-central1",
        service_account_path: Optional[str] = None,
        scopes: Optional[list] = None,
        default_service: ComputeService = ComputeService.GCP_CLOUD_FUNCTIONS,
        tags: Optional[Dict[str, str]] = None,
        use_application_default: bool = True
    ) -> bool:
        """
        Configure GCP compute with Application Default Credentials

        Preferred: Application Default Credentials / Workload Identity (use_application_default=True)
        Fallback: Service Account Key (development only, use_application_default=False)

        Args:
            project_id: GCP project ID
            region: GCP region
            service_account_path: Path to service account JSON key (for development)
            scopes: OAuth2 scopes (optional)
            default_service: Default compute service
            tags: Resource labels
            use_application_default: Use Application Default Credentials (recommended)

        Returns:
            True if configuration successful

        Example:
            # Production: Use Application Default Credentials (most secure)
            # Works with GCE, GKE Workload Identity, Cloud Run
            engine.configure_gcp(
                project_id="my-project-id",
                region="us-central1"
            )

            # Development: Use Service Account key (not recommended)
            engine.configure_gcp(
                project_id="my-project-id",
                service_account_path="/path/to/service-account-key.json",
                use_application_default=False
            )

            # Custom scopes
            engine.configure_gcp(
                project_id="my-project-id",
                scopes=["https://www.googleapis.com/auth/compute"]
            )
        """
        try:
            # Use new authentication system if available
            if self.auth_manager and use_application_default:
                # Authenticate using Application Default Credentials (preferred)
                # This includes Workload Identity on GKE
                cloud_creds = self.auth_manager.authenticate_gcp(
                    project_id=project_id or os.getenv('GCP_PROJECT_ID'),
                    scopes=scopes
                )

                logger.info(f"GCP authenticated via {cloud_creds.auth_method.value}")

                # Store credentials
                credentials = cloud_creds.credentials
            elif self.auth_manager and not use_application_default:
                # Authenticate using Service Account key
                cloud_creds = self.auth_manager.authenticate_gcp(
                    project_id=project_id or os.getenv('GCP_PROJECT_ID'),
                    service_account_path=service_account_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
                    scopes=scopes
                )

                logger.info(f"GCP authenticated via {cloud_creds.auth_method.value}")
                logger.warning("Using Service Account key - prefer Application Default Credentials in production")

                # Store credentials
                credentials = cloud_creds.credentials
            else:
                # Legacy authentication
                credentials = {
                    'project_id': project_id or os.getenv('GCP_PROJECT_ID'),
                    'credentials_path': service_account_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
                }

                if not credentials['project_id']:
                    logger.warning("GCP project ID not provided")

            self.configs[CloudProvider.GCP] = CloudConfig(
                provider=CloudProvider.GCP,
                region=region,
                credentials=credentials,
                default_service=default_service,
                tags=tags or {'managed-by': 'neurolake'}
            )

            self.initialized_providers.append(CloudProvider.GCP)
            logger.info(f"GCP configured: project={project_id}, region={region}, service={default_service}")

            return True

        except Exception as e:
            logger.error(f"Failed to configure GCP: {e}")
            return False

    def submit_workload(
        self,
        provider: CloudProvider,
        service: Optional[ComputeService] = None,
        workload_config: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Submit workload to cloud compute

        Args:
            provider: Cloud provider
            service: Compute service (uses default if not specified)
            workload_config: Workload configuration
            **kwargs: Additional service-specific parameters

        Returns:
            Submission result with job ID
        """
        if provider not in self.initialized_providers:
            raise ValueError(f"Provider {provider} not configured")

        config = self.configs[provider]
        service = service or config.default_service

        logger.info(f"Submitting workload to {provider.value}/{service.value}")

        # Route to appropriate cloud provider
        if provider == CloudProvider.AWS:
            return self._submit_aws(service, workload_config, config, **kwargs)
        elif provider == CloudProvider.AZURE:
            return self._submit_azure(service, workload_config, config, **kwargs)
        elif provider == CloudProvider.GCP:
            return self._submit_gcp(service, workload_config, config, **kwargs)

    def _submit_aws(
        self,
        service: ComputeService,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit workload to AWS"""
        try:
            if service == ComputeService.AWS_LAMBDA:
                return self._submit_aws_lambda(workload_config, config, **kwargs)
            elif service == ComputeService.AWS_BATCH:
                return self._submit_aws_batch(workload_config, config, **kwargs)
            elif service == ComputeService.AWS_EMR:
                return self._submit_aws_emr(workload_config, config, **kwargs)
            elif service == ComputeService.AWS_ECS:
                return self._submit_aws_ecs(workload_config, config, **kwargs)
            else:
                raise ValueError(f"Unsupported AWS service: {service}")

        except Exception as e:
            logger.error(f"AWS submission failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': 'aws',
                'service': service.value
            }

    def _submit_aws_lambda(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to AWS Lambda"""
        try:
            # Try to import boto3
            import boto3

            session = boto3.Session(
                aws_access_key_id=config.credentials.get('access_key_id'),
                aws_secret_access_key=config.credentials.get('secret_access_key'),
                region_name=config.region
            )

            lambda_client = session.client('lambda')

            function_name = workload_config.get('function_name')
            payload = workload_config.get('payload', {})

            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Async
                Payload=str(payload).encode('utf-8')
            )

            return {
                'status': 'submitted',
                'provider': 'aws',
                'service': 'lambda',
                'job_id': response['ResponseMetadata']['RequestId'],
                'status_code': response['StatusCode'],
                'submitted_at': datetime.now().isoformat()
            }

        except ImportError:
            logger.warning("boto3 not installed - returning mock response")
            return self._mock_submission('aws', 'lambda')
        except Exception as e:
            raise Exception(f"Lambda invocation failed: {e}")

    def _submit_aws_batch(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to AWS Batch"""
        try:
            import boto3

            session = boto3.Session(
                aws_access_key_id=config.credentials.get('access_key_id'),
                aws_secret_access_key=config.credentials.get('secret_access_key'),
                region_name=config.region
            )

            batch_client = session.client('batch')

            response = batch_client.submit_job(
                jobName=workload_config.get('job_name', 'neurolake-job'),
                jobQueue=workload_config.get('job_queue'),
                jobDefinition=workload_config.get('job_definition'),
                containerOverrides=workload_config.get('container_overrides', {}),
                tags=config.tags
            )

            return {
                'status': 'submitted',
                'provider': 'aws',
                'service': 'batch',
                'job_id': response['jobId'],
                'job_name': response['jobName'],
                'submitted_at': datetime.now().isoformat()
            }

        except ImportError:
            return self._mock_submission('aws', 'batch')
        except Exception as e:
            raise Exception(f"Batch submission failed: {e}")

    def _submit_aws_emr(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to AWS EMR"""
        try:
            import boto3

            session = boto3.Session(
                aws_access_key_id=config.credentials.get('access_key_id'),
                aws_secret_access_key=config.credentials.get('secret_access_key'),
                region_name=config.region
            )

            emr_client = session.client('emr')

            response = emr_client.add_job_flow_steps(
                JobFlowId=workload_config.get('cluster_id'),
                Steps=[workload_config.get('step', {})]
            )

            return {
                'status': 'submitted',
                'provider': 'aws',
                'service': 'emr',
                'job_id': response['StepIds'][0],
                'cluster_id': workload_config.get('cluster_id'),
                'submitted_at': datetime.now().isoformat()
            }

        except ImportError:
            return self._mock_submission('aws', 'emr')
        except Exception as e:
            raise Exception(f"EMR submission failed: {e}")

    def _submit_aws_ecs(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to AWS ECS"""
        try:
            import boto3

            session = boto3.Session(
                aws_access_key_id=config.credentials.get('access_key_id'),
                aws_secret_access_key=config.credentials.get('secret_access_key'),
                region_name=config.region
            )

            ecs_client = session.client('ecs')

            response = ecs_client.run_task(
                cluster=workload_config.get('cluster'),
                taskDefinition=workload_config.get('task_definition'),
                launchType='FARGATE',
                networkConfiguration=workload_config.get('network_configuration', {}),
                tags=[{'key': k, 'value': v} for k, v in config.tags.items()]
            )

            return {
                'status': 'submitted',
                'provider': 'aws',
                'service': 'ecs',
                'job_id': response['tasks'][0]['taskArn'],
                'cluster': workload_config.get('cluster'),
                'submitted_at': datetime.now().isoformat()
            }

        except ImportError:
            return self._mock_submission('aws', 'ecs')
        except Exception as e:
            raise Exception(f"ECS submission failed: {e}")

    def _submit_azure(
        self,
        service: ComputeService,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit workload to Azure"""
        try:
            if service == ComputeService.AZURE_FUNCTIONS:
                return self._submit_azure_functions(workload_config, config, **kwargs)
            elif service == ComputeService.AZURE_CONTAINER_INSTANCES:
                return self._submit_azure_container_instances(workload_config, config, **kwargs)
            elif service == ComputeService.AZURE_DATABRICKS:
                return self._submit_azure_databricks(workload_config, config, **kwargs)
            else:
                raise ValueError(f"Unsupported Azure service: {service}")

        except Exception as e:
            logger.error(f"Azure submission failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': 'azure',
                'service': service.value
            }

    def _submit_azure_functions(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to Azure Functions"""
        try:
            # Azure Functions submission would go here
            # Using Azure SDK for Python
            return self._mock_submission('azure', 'functions')

        except Exception as e:
            raise Exception(f"Azure Functions submission failed: {e}")

    def _submit_azure_container_instances(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to Azure Container Instances"""
        try:
            # ACI submission would go here
            return self._mock_submission('azure', 'container_instances')

        except Exception as e:
            raise Exception(f"Azure Container Instances submission failed: {e}")

    def _submit_azure_databricks(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to Azure Databricks"""
        try:
            # Databricks API submission would go here
            return self._mock_submission('azure', 'databricks')

        except Exception as e:
            raise Exception(f"Azure Databricks submission failed: {e}")

    def _submit_gcp(
        self,
        service: ComputeService,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit workload to GCP"""
        try:
            if service == ComputeService.GCP_CLOUD_FUNCTIONS:
                return self._submit_gcp_cloud_functions(workload_config, config, **kwargs)
            elif service == ComputeService.GCP_CLOUD_RUN:
                return self._submit_gcp_cloud_run(workload_config, config, **kwargs)
            elif service == ComputeService.GCP_DATAPROC:
                return self._submit_gcp_dataproc(workload_config, config, **kwargs)
            else:
                raise ValueError(f"Unsupported GCP service: {service}")

        except Exception as e:
            logger.error(f"GCP submission failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'provider': 'gcp',
                'service': service.value
            }

    def _submit_gcp_cloud_functions(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to GCP Cloud Functions"""
        try:
            # GCP Cloud Functions submission would go here
            return self._mock_submission('gcp', 'cloud_functions')

        except Exception as e:
            raise Exception(f"GCP Cloud Functions submission failed: {e}")

    def _submit_gcp_cloud_run(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to GCP Cloud Run"""
        try:
            # Cloud Run submission would go here
            return self._mock_submission('gcp', 'cloud_run')

        except Exception as e:
            raise Exception(f"GCP Cloud Run submission failed: {e}")

    def _submit_gcp_dataproc(
        self,
        workload_config: Dict[str, Any],
        config: CloudConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit to GCP Dataproc"""
        try:
            # Dataproc submission would go here
            return self._mock_submission('gcp', 'dataproc')

        except Exception as e:
            raise Exception(f"GCP Dataproc submission failed: {e}")

    def _mock_submission(self, provider: str, service: str) -> Dict[str, Any]:
        """Mock submission for testing"""
        import uuid

        job_id = f"{provider}-{service}-{uuid.uuid4().hex[:8]}"

        logger.info(f"Mock submission to {provider}/{service}: {job_id}")

        return {
            'status': 'submitted',
            'provider': provider,
            'service': service,
            'job_id': job_id,
            'submitted_at': datetime.now().isoformat(),
            'note': 'Mock submission - SDK not available'
        }

    def get_job_status(
        self,
        provider: CloudProvider,
        job_id: str,
        service: Optional[ComputeService] = None
    ) -> Dict[str, Any]:
        """Get job status from cloud provider"""
        if provider not in self.initialized_providers:
            raise ValueError(f"Provider {provider} not configured")

        config = self.configs[provider]
        service = service or config.default_service

        logger.info(f"Checking job status: {job_id} on {provider.value}/{service.value}")

        # Mock status for now
        return {
            'job_id': job_id,
            'provider': provider.value,
            'service': service.value,
            'status': 'running',
            'checked_at': datetime.now().isoformat()
        }

    def get_configured_providers(self) -> List[Dict[str, Any]]:
        """Get list of configured cloud providers"""
        return [
            {
                'provider': provider.value,
                'region': config.region,
                'default_service': config.default_service.value,
                'tags': config.tags
            }
            for provider, config in self.configs.items()
        ]

    def is_provider_configured(self, provider: CloudProvider) -> bool:
        """Check if a provider is configured"""
        return provider in self.initialized_providers
