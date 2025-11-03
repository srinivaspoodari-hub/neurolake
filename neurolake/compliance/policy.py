"""
Policy Engine

Manages and enforces data policies and compliance rules.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """Types of policies."""
    ACCESS_CONTROL = "access_control"
    DATA_RETENTION = "data_retention"
    PII_PROTECTION = "pii_protection"
    ENCRYPTION = "encryption"
    AUDIT = "audit"
    CUSTOM = "custom"


class PolicySeverity(Enum):
    """Severity levels for policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Policy:
    """A compliance policy."""
    name: str
    policy_type: PolicyType
    description: str
    check_function: Callable[[Any], bool]
    severity: PolicySeverity = PolicySeverity.ERROR
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def check(self, data: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if data complies with policy.

        Args:
            data: Data to check
            context: Optional context

        Returns:
            True if compliant
        """
        if not self.enabled:
            return True

        try:
            return self.check_function(data, context) if context else self.check_function(data)
        except TypeError:
            # Handle functions that don't accept context
            return self.check_function(data)
        except Exception as e:
            logger.error(f"Error checking policy {self.name}: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "policy_type": self.policy_type.value,
            "description": self.description,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PolicyViolation:
    """A policy violation record."""
    policy_name: str
    severity: PolicySeverity
    description: str
    data_context: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_name": self.policy_name,
            "severity": self.severity.value,
            "description": self.description,
            "data_context": self.data_context,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class PolicyEngine:
    """
    Engine for managing and enforcing policies.

    Example:
        engine = PolicyEngine()

        # Add policy
        def no_pii_policy(data):
            return not compliance_engine.contains_pii(data)

        engine.add_policy(
            name="no_pii",
            policy_type="pii_protection",
            description="No PII allowed",
            check_function=no_pii_policy
        )

        # Check compliance
        result = engine.check_compliance("Test data")
        if not result.compliant:
            print(f"Violations: {result.violations}")
    """

    def __init__(self):
        """Initialize policy engine."""
        self.policies: Dict[str, Policy] = {}
        self.violations: List[PolicyViolation] = []
        self._compliance_engine = None

    def set_compliance_engine(self, engine):
        """Set reference to compliance engine for PII checks."""
        self._compliance_engine = engine

    def add_policy(
        self,
        name: str,
        policy_type: str,
        description: str,
        check_function: Callable[[Any], bool],
        severity: str = "error",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Policy:
        """
        Add a new policy.

        Args:
            name: Policy name
            policy_type: Type of policy
            description: Policy description
            check_function: Function to check compliance
            severity: Severity level
            metadata: Additional metadata

        Returns:
            Created policy
        """
        policy = Policy(
            name=name,
            policy_type=PolicyType[policy_type.upper()] if isinstance(policy_type, str) else policy_type,
            description=description,
            check_function=check_function,
            severity=PolicySeverity[severity.upper()] if isinstance(severity, str) else severity,
            metadata=metadata or {}
        )

        self.policies[name] = policy
        logger.info(f"Added policy: {name}")
        return policy

    def remove_policy(self, name: str):
        """Remove a policy."""
        if name in self.policies:
            del self.policies[name]
            logger.info(f"Removed policy: {name}")

    def enable_policy(self, name: str):
        """Enable a policy."""
        if name in self.policies:
            self.policies[name].enabled = True

    def disable_policy(self, name: str):
        """Disable a policy."""
        if name in self.policies:
            self.policies[name].enabled = False

    def get_policy(self, name: str) -> Optional[Policy]:
        """Get a policy by name."""
        return self.policies.get(name)

    def list_policies(
        self,
        policy_type: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[Policy]:
        """
        List all policies.

        Args:
            policy_type: Filter by policy type
            enabled_only: Only return enabled policies

        Returns:
            List of policies
        """
        policies = list(self.policies.values())

        if policy_type:
            policy_type_enum = PolicyType[policy_type.upper()]
            policies = [p for p in policies if p.policy_type == policy_type_enum]

        if enabled_only:
            policies = [p for p in policies if p.enabled]

        return policies

    def check_compliance(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        policy_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check data compliance against policies.

        Args:
            data: Data to check
            context: Optional context
            policy_names: Specific policies to check

        Returns:
            Compliance result with violations
        """
        violations = []
        policies_to_check = []

        if policy_names:
            policies_to_check = [
                self.policies[name] for name in policy_names
                if name in self.policies
            ]
        else:
            policies_to_check = [p for p in self.policies.values() if p.enabled]

        # Check each policy
        for policy in policies_to_check:
            if not policy.check(data, context):
                violation = PolicyViolation(
                    policy_name=policy.name,
                    severity=policy.severity,
                    description=f"Policy '{policy.name}' violated: {policy.description}",
                    data_context=str(data)[:100] if data else None,
                    metadata={"policy_type": policy.policy_type.value}
                )
                violations.append(violation)
                self.violations.append(violation)

        return {
            "compliant": len(violations) == 0,
            "violations": [v.to_dict() for v in violations],
            "policies_checked": len(policies_to_check),
            "timestamp": datetime.now().isoformat()
        }

    def enforce_policies(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        raise_on_violation: bool = True
    ) -> bool:
        """
        Enforce policies and optionally raise exception on violation.

        Args:
            data: Data to check
            context: Optional context
            raise_on_violation: Raise exception if policy violated

        Returns:
            True if compliant

        Raises:
            PolicyViolationError: If policy violated and raise_on_violation=True
        """
        result = self.check_compliance(data, context)

        if not result["compliant"] and raise_on_violation:
            violations_str = "\n".join([
                f"- {v['policy_name']}: {v['description']}"
                for v in result["violations"]
            ])
            raise PolicyViolationError(
                f"Policy violations detected:\n{violations_str}"
            )

        return result["compliant"]

    def get_violations(
        self,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[PolicyViolation]:
        """
        Get recent violations.

        Args:
            severity: Filter by severity
            limit: Maximum violations to return

        Returns:
            List of violations
        """
        violations = self.violations

        if severity:
            severity_enum = PolicySeverity[severity.upper()]
            violations = [v for v in violations if v.severity == severity_enum]

        # Return most recent first
        violations = sorted(violations, key=lambda x: x.timestamp, reverse=True)
        return violations[:limit]

    def clear_violations(self):
        """Clear all recorded violations."""
        self.violations.clear()

    def add_builtin_policies(self, compliance_engine=None):
        """
        Add built-in policies.

        Args:
            compliance_engine: ComplianceEngine instance for PII checks
        """
        if compliance_engine:
            self._compliance_engine = compliance_engine

        # No PII policy
        if self._compliance_engine:
            self.add_policy(
                name="no_pii",
                policy_type="pii_protection",
                description="Data must not contain PII",
                check_function=lambda data: not self._compliance_engine.contains_pii(str(data)),
                severity="critical"
            )

        # No empty data policy
        self.add_policy(
            name="no_empty_data",
            policy_type="custom",
            description="Data must not be empty",
            check_function=lambda data: data is not None and len(str(data).strip()) > 0,
            severity="warning"
        )

        # Max length policy
        self.add_policy(
            name="max_length",
            policy_type="custom",
            description="Data must not exceed maximum length",
            check_function=lambda data: len(str(data)) <= 10000,
            severity="warning"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get policy engine statistics.

        Returns:
            Statistics dictionary
        """
        total_policies = len(self.policies)
        enabled_policies = len([p for p in self.policies.values() if p.enabled])

        violation_counts = {}
        for violation in self.violations:
            severity = violation.severity.value
            violation_counts[severity] = violation_counts.get(severity, 0) + 1

        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "disabled_policies": total_policies - enabled_policies,
            "total_violations": len(self.violations),
            "violations_by_severity": violation_counts,
            "policies_by_type": self._count_by_type()
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count policies by type."""
        counts = {}
        for policy in self.policies.values():
            policy_type = policy.policy_type.value
            counts[policy_type] = counts.get(policy_type, 0) + 1
        return counts


class PolicyViolationError(Exception):
    """Exception raised when policy is violated."""
    pass


__all__ = [
    "PolicyEngine",
    "Policy",
    "PolicyViolation",
    "PolicyType",
    "PolicySeverity",
    "PolicyViolationError"
]
