"""
Environment Configuration

Manages production vs development settings with strict cloud enforcement.
Integrates with RBAC for admin-controlled configuration.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Literal
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class Permission(str, Enum):
    """System permissions"""
    # Admin permissions
    ADMIN_FULL = "admin:full"
    ADMIN_CONFIG = "admin:config"
    ADMIN_USERS = "admin:users"

    # Compute permissions
    COMPUTE_LOCAL = "compute:local"
    COMPUTE_CLOUD = "compute:cloud"
    COMPUTE_CONFIGURE = "compute:configure"

    # Storage permissions
    STORAGE_LOCAL = "storage:local"
    STORAGE_CLOUD = "storage:cloud"
    STORAGE_CONFIGURE = "storage:configure"

    # Environment permissions
    ENV_CHANGE = "env:change"
    ENV_VIEW = "env:view"


@dataclass
class EnvironmentConfig:
    """Environment configuration"""
    environment: Environment

    # Compute settings
    compute_allow_local: bool
    compute_cloud_required: bool
    compute_default_cloud: CloudProvider
    compute_allowed_clouds: List[CloudProvider]

    # Storage settings
    storage_allow_local: bool
    storage_cloud_required: bool
    storage_default_cloud: CloudProvider
    storage_allowed_clouds: List[CloudProvider]

    # Admin settings
    admin_email: Optional[str]
    config_locked: bool  # If true, only admin can change

    # Metadata
    last_updated: str
    updated_by: Optional[str]


class EnvironmentManager:
    """
    Environment Manager

    Manages environment configuration with production enforcement:
    - Production: Cloud-only, admin-configurable
    - Staging: Flexible, some restrictions
    - Development: Full flexibility
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize environment manager

        Args:
            config_path: Path to environment config file
        """
        self.config_path = Path(config_path or "./config/environment.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Detect environment from ENV var or config
        self.current_env = self._detect_environment()

        # Load or create config
        self.config = self._load_or_create_config()

        logger.info(f"Environment: {self.current_env.value}")
        logger.info(f"Compute: {'Cloud-only' if self.config.compute_cloud_required else 'Hybrid'}")
        logger.info(f"Storage: {'Cloud-only' if self.config.storage_cloud_required else 'Hybrid'}")

    def _detect_environment(self) -> Environment:
        """Detect current environment"""
        # Check environment variable
        env_str = os.getenv("NEUROLAKE_ENV", "development").lower()

        if env_str in ["prod", "production"]:
            return Environment.PRODUCTION
        elif env_str in ["stage", "staging"]:
            return Environment.STAGING
        else:
            return Environment.DEVELOPMENT

    def _load_or_create_config(self) -> EnvironmentConfig:
        """Load existing config or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)

                # Convert string enums back to enum types
                data['environment'] = Environment(data['environment'])
                data['compute_default_cloud'] = CloudProvider(data['compute_default_cloud'])
                data['storage_default_cloud'] = CloudProvider(data['storage_default_cloud'])
                data['compute_allowed_clouds'] = [CloudProvider(c) for c in data['compute_allowed_clouds']]
                data['storage_allowed_clouds'] = [CloudProvider(c) for c in data['storage_allowed_clouds']]

                config = EnvironmentConfig(**data)
                logger.info("Loaded existing environment config")
                return config

            except Exception as e:
                logger.error(f"Failed to load config: {e}, creating default")

        # Create default config based on environment
        return self._create_default_config()

    def _create_default_config(self) -> EnvironmentConfig:
        """Create default configuration based on environment"""
        from datetime import datetime

        if self.current_env == Environment.PRODUCTION:
            # PRODUCTION: Strict cloud-only
            config = EnvironmentConfig(
                environment=Environment.PRODUCTION,
                compute_allow_local=False,  # No local compute in prod
                compute_cloud_required=True,  # Must use cloud
                compute_default_cloud=CloudProvider.AWS,
                compute_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                storage_allow_local=False,  # No local storage in prod
                storage_cloud_required=True,  # Must use cloud
                storage_default_cloud=CloudProvider.AWS,
                storage_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                admin_email=os.getenv("ADMIN_EMAIL"),
                config_locked=True,  # Locked - admin only
                last_updated=datetime.now().isoformat(),
                updated_by="system_default"
            )

        elif self.current_env == Environment.STAGING:
            # STAGING: Prefer cloud, allow local for testing
            config = EnvironmentConfig(
                environment=Environment.STAGING,
                compute_allow_local=True,  # Can use local for testing
                compute_cloud_required=False,  # Cloud not required
                compute_default_cloud=CloudProvider.AWS,
                compute_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                storage_allow_local=True,
                storage_cloud_required=False,
                storage_default_cloud=CloudProvider.AWS,
                storage_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                admin_email=os.getenv("ADMIN_EMAIL"),
                config_locked=False,  # Not locked
                last_updated=datetime.now().isoformat(),
                updated_by="system_default"
            )

        else:  # DEVELOPMENT
            # DEVELOPMENT: Full flexibility
            config = EnvironmentConfig(
                environment=Environment.DEVELOPMENT,
                compute_allow_local=True,  # Local preferred for dev
                compute_cloud_required=False,  # Cloud optional
                compute_default_cloud=CloudProvider.AWS,
                compute_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                storage_allow_local=True,
                storage_cloud_required=False,
                storage_default_cloud=CloudProvider.AWS,
                storage_allowed_clouds=[CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP],
                admin_email=os.getenv("ADMIN_EMAIL"),
                config_locked=False,
                last_updated=datetime.now().isoformat(),
                updated_by="system_default"
            )

        # Save default config
        self._save_config(config)
        logger.info(f"Created default {self.current_env.value} config")

        return config

    def _save_config(self, config: EnvironmentConfig):
        """Save configuration to file"""
        try:
            # Convert to dict and handle enums
            data = asdict(config)
            data['environment'] = config.environment.value
            data['compute_default_cloud'] = config.compute_default_cloud.value
            data['storage_default_cloud'] = config.storage_default_cloud.value
            data['compute_allowed_clouds'] = [c.value for c in config.compute_allowed_clouds]
            data['storage_allowed_clouds'] = [c.value for c in config.storage_allowed_clouds]

            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info("Environment config saved")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.current_env == Environment.PRODUCTION

    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.current_env == Environment.STAGING

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.current_env == Environment.DEVELOPMENT

    def can_use_local_compute(self, user_permissions: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Check if local compute is allowed

        Args:
            user_permissions: List of user permissions

        Returns:
            Dict with allowed status and reason
        """
        # Production: Never allow local compute
        if self.is_production():
            return {
                'allowed': False,
                'reason': 'Production environment requires cloud compute only',
                'alternative': f'Use {self.config.compute_default_cloud.value.upper()} compute'
            }

        # Check configuration
        if not self.config.compute_allow_local:
            return {
                'allowed': False,
                'reason': 'Local compute disabled in environment configuration',
                'alternative': 'Contact admin to enable or use cloud'
            }

        # Check user permissions if provided
        if user_permissions and Permission.COMPUTE_LOCAL.value not in user_permissions:
            return {
                'allowed': False,
                'reason': 'User does not have local compute permissions',
                'alternative': 'Request COMPUTE_LOCAL permission or use cloud'
            }

        return {
            'allowed': True,
            'reason': 'Local compute allowed in current environment'
        }

    def can_use_local_storage(self, user_permissions: Optional[List[str]] = None) -> Dict[str, any]:
        """Check if local storage is allowed"""
        # Production: Never allow local storage
        if self.is_production():
            return {
                'allowed': False,
                'reason': 'Production environment requires cloud storage only',
                'alternative': f'Use {self.config.storage_default_cloud.value.upper()} storage'
            }

        # Check configuration
        if not self.config.storage_allow_local:
            return {
                'allowed': False,
                'reason': 'Local storage disabled in environment configuration',
                'alternative': 'Contact admin to enable or use cloud'
            }

        # Check user permissions if provided
        if user_permissions and Permission.STORAGE_LOCAL.value not in user_permissions:
            return {
                'allowed': False,
                'reason': 'User does not have local storage permissions',
                'alternative': 'Request STORAGE_LOCAL permission or use cloud'
            }

        return {
            'allowed': True,
            'reason': 'Local storage allowed in current environment'
        }

    def get_allowed_cloud_providers(self, resource_type: Literal["compute", "storage"]) -> List[CloudProvider]:
        """Get list of allowed cloud providers for a resource type"""
        if resource_type == "compute":
            return self.config.compute_allowed_clouds
        else:
            return self.config.storage_allowed_clouds

    def get_default_cloud_provider(self, resource_type: Literal["compute", "storage"]) -> CloudProvider:
        """Get default cloud provider for a resource type"""
        if resource_type == "compute":
            return self.config.compute_default_cloud
        else:
            return self.config.storage_default_cloud

    def update_config(
        self,
        user_permissions: List[str],
        user_id: str,
        **updates
    ) -> Dict[str, any]:
        """
        Update environment configuration

        Requires admin permissions. Production config is locked unless admin.

        Args:
            user_permissions: User's permissions
            user_id: User making the change
            **updates: Configuration updates

        Returns:
            Result with success/failure
        """
        # Check if user is admin
        is_admin = (
            Permission.ADMIN_FULL.value in user_permissions or
            Permission.ADMIN_CONFIG.value in user_permissions
        )

        if not is_admin:
            return {
                'success': False,
                'reason': 'Admin permissions required to modify environment configuration'
            }

        # In production, extra check for locked config
        if self.config.config_locked and not Permission.ADMIN_FULL.value in user_permissions:
            return {
                'success': False,
                'reason': 'Configuration is locked. ADMIN_FULL permission required.'
            }

        # Update configuration
        from datetime import datetime

        for key, value in updates.items():
            if hasattr(self.config, key):
                # Handle enum conversions
                if 'cloud' in key and isinstance(value, str):
                    value = CloudProvider(value)
                elif key == 'environment' and isinstance(value, str):
                    value = Environment(value)

                setattr(self.config, key, value)

        # Update metadata
        self.config.last_updated = datetime.now().isoformat()
        self.config.updated_by = user_id

        # Save
        self._save_config(self.config)

        logger.info(f"Config updated by {user_id}: {updates}")

        return {
            'success': True,
            'message': 'Configuration updated successfully',
            'updated_by': user_id
        }

    def get_config_summary(self) -> Dict[str, any]:
        """Get configuration summary"""
        return {
            'environment': self.config.environment.value,
            'compute': {
                'local_allowed': self.config.compute_allow_local,
                'cloud_required': self.config.compute_cloud_required,
                'default_cloud': self.config.compute_default_cloud.value,
                'allowed_clouds': [c.value for c in self.config.compute_allowed_clouds]
            },
            'storage': {
                'local_allowed': self.config.storage_allow_local,
                'cloud_required': self.config.storage_cloud_required,
                'default_cloud': self.config.storage_default_cloud.value,
                'allowed_clouds': [c.value for c in self.config.storage_allowed_clouds]
            },
            'admin': {
                'email': self.config.admin_email,
                'config_locked': self.config.config_locked
            },
            'metadata': {
                'last_updated': self.config.last_updated,
                'updated_by': self.config.updated_by
            }
        }

    def enforce_production_rules(self) -> Dict[str, any]:
        """
        Enforce production rules

        Ensures production environment has cloud-only settings.
        Called during startup and configuration changes.

        Returns:
            Enforcement result
        """
        if not self.is_production():
            return {
                'enforced': False,
                'reason': 'Not in production environment'
            }

        violations = []

        # Check compute
        if self.config.compute_allow_local:
            violations.append('compute_allow_local must be False in production')
            self.config.compute_allow_local = False

        if not self.config.compute_cloud_required:
            violations.append('compute_cloud_required must be True in production')
            self.config.compute_cloud_required = True

        # Check storage
        if self.config.storage_allow_local:
            violations.append('storage_allow_local must be False in production')
            self.config.storage_allow_local = False

        if not self.config.storage_cloud_required:
            violations.append('storage_cloud_required must be True in production')
            self.config.storage_cloud_required = True

        if violations:
            logger.warning(f"Production rules enforced: {violations}")
            self._save_config(self.config)

            return {
                'enforced': True,
                'violations_fixed': violations,
                'message': 'Production configuration enforced: cloud-only mode activated'
            }

        return {
            'enforced': True,
            'violations_fixed': [],
            'message': 'Production configuration compliant'
        }


# Global environment manager instance
_env_manager: Optional[EnvironmentManager] = None


def get_environment_manager() -> EnvironmentManager:
    """Get global environment manager instance"""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvironmentManager()
        # Enforce production rules on startup
        if _env_manager.is_production():
            _env_manager.enforce_production_rules()
    return _env_manager
