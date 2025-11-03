"""
NeuroLake Compliance Module

Provides PII detection, policy enforcement, data masking, and audit logging.

Example:
    from neurolake.compliance import ComplianceEngine, PolicyEngine, AuditLogger

    # Create compliance engine
    engine = ComplianceEngine()

    # Detect PII
    pii_results = engine.detect_pii("John Smith's SSN is 123-45-6789")

    # Check policies
    policy_engine = PolicyEngine()
    policy_engine.add_policy("no_pii", lambda data: not has_pii(data))

    # Mask sensitive data
    masked = engine.mask_data(text, pii_results)

    # Audit logging
    logger = AuditLogger()
    logger.log_access("user_table", "SELECT", user="john@example.com")
"""

from neurolake.compliance.engine import ComplianceEngine, PIIResult
from neurolake.compliance.policy import PolicyEngine, Policy, PolicyViolation
from neurolake.compliance.masking import DataMasker, MaskingStrategy, MaskingConfig
from neurolake.compliance.audit import AuditLogger, AuditEvent

__all__ = [
    "ComplianceEngine",
    "PIIResult",
    "PolicyEngine",
    "Policy",
    "PolicyViolation",
    "DataMasker",
    "MaskingStrategy",
    "MaskingConfig",
    "AuditLogger",
    "AuditEvent",
]
