"""
Compliance API Router (v1)

Compliance policy management and PII detection endpoints.
Handles data compliance checks, policy enforcement, and PII detection.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam, status
from pydantic import BaseModel, Field
from datetime import datetime

from neurolake.auth.models import User
from neurolake.api.dependencies import get_current_active_user, PermissionChecker
from neurolake.compliance import ComplianceEngine, PolicyEngine
from neurolake.compliance.policy import PolicyType, PolicySeverity

logger = logging.getLogger(__name__)
router = APIRouter()

# Global singleton instances
_compliance_engine = None
_policy_engine = None


def get_compliance_engine() -> ComplianceEngine:
    """Get or create compliance engine singleton."""
    global _compliance_engine
    if _compliance_engine is None:
        _compliance_engine = ComplianceEngine()
    return _compliance_engine


def get_policy_engine() -> PolicyEngine:
    """Get or create policy engine singleton."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
        # Set compliance engine reference
        _policy_engine.set_compliance_engine(get_compliance_engine())
        # Add built-in policies
        _policy_engine.add_builtin_policies(get_compliance_engine())
    return _policy_engine


# Pydantic Models

class PIIDetectionRequest(BaseModel):
    """PII detection request."""
    text: str = Field(..., min_length=1, description="Text to analyze for PII")
    language: str = Field("en", description="Language code")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="Confidence threshold")
    entities: Optional[List[str]] = Field(None, description="Specific entity types to detect")


class PIIDetectionResult(BaseModel):
    """PII detection result."""
    entity_type: str
    text: str
    start: int
    end: int
    confidence: float
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PIIDetectionResponse(BaseModel):
    """PII detection response."""
    found_pii: bool
    pii_count: int
    pii_types: List[str]
    results: List[PIIDetectionResult]


class PIIMaskRequest(BaseModel):
    """PII masking request."""
    text: str = Field(..., min_length=1)
    mask_char: str = Field("*", min_length=1, max_length=1)
    anonymize: bool = Field(False, description="Use type labels instead of mask chars")


class PIIMaskResponse(BaseModel):
    """PII masking response."""
    original_length: int
    masked_text: str
    pii_found: int


class PolicyCreateRequest(BaseModel):
    """Policy creation request using predefined templates."""
    name: str = Field(..., min_length=1, max_length=100)
    policy_type: str = Field(..., pattern="^(access_control|data_retention|pii_protection|encryption|audit|custom)$")
    description: str = Field(..., min_length=1)
    template: str = Field(..., description="Policy template: no_pii, no_empty_data, max_length, contains_keyword, min_length")
    severity: str = Field("error", pattern="^(info|warning|error|critical)$")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Template parameters")


class PolicyResponse(BaseModel):
    """Policy response."""
    name: str
    policy_type: str
    description: str
    severity: str
    enabled: bool
    created_at: str
    metadata: Dict[str, Any] = {}


class PolicyListResponse(BaseModel):
    """Policy list response."""
    policies: List[PolicyResponse]
    total: int


class PolicyUpdateRequest(BaseModel):
    """Policy update request."""
    enabled: Optional[bool] = None
    description: Optional[str] = None


class ComplianceCheckRequest(BaseModel):
    """Compliance check request."""
    data: str = Field(..., description="Data to check for compliance")
    policy_names: Optional[List[str]] = Field(None, description="Specific policies to check")


class ComplianceCheckResponse(BaseModel):
    """Compliance check response."""
    compliant: bool
    violations: List[Dict[str, Any]]
    policies_checked: int
    timestamp: str


class ViolationResponse(BaseModel):
    """Violation response."""
    policy_name: str
    severity: str
    description: str
    data_context: Optional[str]
    timestamp: str
    metadata: Dict[str, Any] = {}


class ViolationListResponse(BaseModel):
    """Violation list response."""
    violations: List[ViolationResponse]
    total: int


class ComplianceStatsResponse(BaseModel):
    """Compliance statistics response."""
    total_policies: int
    enabled_policies: int
    disabled_policies: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    policies_by_type: Dict[str, int]
    presidio_enabled: bool
    supported_entities: int


# Policy template functions
def create_policy_function(template: str, parameters: Dict[str, Any]):
    """Create a policy check function from template."""
    compliance_engine = get_compliance_engine()

    if template == "no_pii":
        return lambda data: not compliance_engine.contains_pii(str(data))

    elif template == "no_empty_data":
        return lambda data: data is not None and len(str(data).strip()) > 0

    elif template == "max_length":
        max_len = parameters.get("max_length", 10000)
        return lambda data: len(str(data)) <= max_len

    elif template == "min_length":
        min_len = parameters.get("min_length", 1)
        return lambda data: len(str(data)) >= min_len

    elif template == "contains_keyword":
        keyword = parameters.get("keyword", "")
        return lambda data: keyword.lower() in str(data).lower()

    elif template == "not_contains_keyword":
        keyword = parameters.get("keyword", "")
        return lambda data: keyword.lower() not in str(data).lower()

    elif template == "regex_match":
        import re
        pattern = parameters.get("pattern", ".*")
        regex = re.compile(pattern)
        return lambda data: regex.search(str(data)) is not None

    else:
        raise ValueError(f"Unknown policy template: {template}")


# Endpoints

@router.post("/detect-pii", response_model=PIIDetectionResponse, summary="Detect PII")
async def detect_pii(
    request: PIIDetectionRequest,
    current_user: User = Depends(get_current_active_user)
) -> PIIDetectionResponse:
    """
    Detect PII (Personally Identifiable Information) in text.

    **Required:** Authenticated user

    Returns detected PII entities with confidence scores.
    """
    try:
        engine = get_compliance_engine()

        # Detect PII
        results = engine.detect_pii(
            text=request.text,
            language=request.language,
            entities=request.entities,
            threshold=request.threshold
        )

        # Convert results
        pii_results = [
            PIIDetectionResult(
                entity_type=r.entity_type.value,
                text=r.text,
                start=r.start,
                end=r.end,
                confidence=r.confidence,
                context=r.context,
                metadata=r.metadata
            )
            for r in results
        ]

        pii_types = list(set(r.entity_type for r in pii_results))

        return PIIDetectionResponse(
            found_pii=len(pii_results) > 0,
            pii_count=len(pii_results),
            pii_types=pii_types,
            results=pii_results
        )

    except Exception as e:
        logger.error(f"Failed to detect PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mask-pii", response_model=PIIMaskResponse, summary="Mask PII")
async def mask_pii(
    request: PIIMaskRequest,
    current_user: User = Depends(get_current_active_user)
) -> PIIMaskResponse:
    """
    Mask or anonymize PII in text.

    **Required:** Authenticated user

    Returns text with PII masked or anonymized.
    """
    try:
        engine = get_compliance_engine()

        # Detect PII
        pii_results = engine.detect_pii(request.text)

        # Mask or anonymize
        if request.anonymize:
            masked_text = engine.anonymize_data(request.text, pii_results)
        else:
            masked_text = engine.mask_data(request.text, pii_results, request.mask_char)

        return PIIMaskResponse(
            original_length=len(request.text),
            masked_text=masked_text,
            pii_found=len(pii_results)
        )

    except Exception as e:
        logger.error(f"Failed to mask PII: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policies", response_model=PolicyListResponse, summary="List Policies")
async def list_policies(
    policy_type: Optional[str] = QueryParam(None, description="Filter by policy type"),
    enabled_only: bool = QueryParam(False, description="Only return enabled policies"),
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> PolicyListResponse:
    """
    List all compliance policies.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()
        policies = engine.list_policies(policy_type=policy_type, enabled_only=enabled_only)

        policy_responses = [
            PolicyResponse(
                name=p.name,
                policy_type=p.policy_type.value,
                description=p.description,
                severity=p.severity.value,
                enabled=p.enabled,
                created_at=p.created_at.isoformat(),
                metadata=p.metadata
            )
            for p in policies
        ]

        return PolicyListResponse(
            policies=policy_responses,
            total=len(policy_responses)
        )

    except Exception as e:
        logger.error(f"Failed to list policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED, summary="Create Policy")
async def create_policy(
    request: PolicyCreateRequest,
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> PolicyResponse:
    """
    Create a new compliance policy from template.

    **Required Permission:** `admin:system`

    Available templates:
    - `no_pii`: Check that data contains no PII
    - `no_empty_data`: Check that data is not empty
    - `max_length`: Check maximum length (params: max_length)
    - `min_length`: Check minimum length (params: min_length)
    - `contains_keyword`: Check data contains keyword (params: keyword)
    - `not_contains_keyword`: Check data doesn't contain keyword (params: keyword)
    - `regex_match`: Check data matches regex (params: pattern)
    """
    try:
        engine = get_policy_engine()

        # Check if policy exists
        if engine.get_policy(request.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Policy '{request.name}' already exists"
            )

        # Create check function from template
        try:
            check_function = create_policy_function(request.template, request.parameters)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Add policy
        metadata = request.parameters.copy()
        metadata["template"] = request.template

        policy = engine.add_policy(
            name=request.name,
            policy_type=request.policy_type,
            description=request.description,
            check_function=check_function,
            severity=request.severity,
            metadata=metadata
        )

        return PolicyResponse(
            name=policy.name,
            policy_type=policy.policy_type.value,
            description=policy.description,
            severity=policy.severity.value,
            enabled=policy.enabled,
            created_at=policy.created_at.isoformat(),
            metadata=policy.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policies/{policy_name}", response_model=PolicyResponse, summary="Get Policy")
async def get_policy(
    policy_name: str,
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> PolicyResponse:
    """
    Get a specific policy by name.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()
        policy = engine.get_policy(policy_name)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_name}' not found")

        return PolicyResponse(
            name=policy.name,
            policy_type=policy.policy_type.value,
            description=policy.description,
            severity=policy.severity.value,
            enabled=policy.enabled,
            created_at=policy.created_at.isoformat(),
            metadata=policy.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/policies/{policy_name}", response_model=PolicyResponse, summary="Update Policy")
async def update_policy(
    policy_name: str,
    request: PolicyUpdateRequest,
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> PolicyResponse:
    """
    Update policy configuration.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()
        policy = engine.get_policy(policy_name)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy '{policy_name}' not found")

        # Update fields
        if request.enabled is not None:
            if request.enabled:
                engine.enable_policy(policy_name)
            else:
                engine.disable_policy(policy_name)
            policy.enabled = request.enabled

        if request.description is not None:
            policy.description = request.description

        return PolicyResponse(
            name=policy.name,
            policy_type=policy.policy_type.value,
            description=policy.description,
            severity=policy.severity.value,
            enabled=policy.enabled,
            created_at=policy.created_at.isoformat(),
            metadata=policy.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/policies/{policy_name}", summary="Delete Policy")
async def delete_policy(
    policy_name: str,
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> Dict[str, str]:
    """
    Delete a policy.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()

        if not engine.get_policy(policy_name):
            raise HTTPException(status_code=404, detail=f"Policy '{policy_name}' not found")

        engine.remove_policy(policy_name)

        return {"message": f"Policy '{policy_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check", response_model=ComplianceCheckResponse, summary="Check Compliance")
async def check_compliance(
    request: ComplianceCheckRequest,
    current_user: User = Depends(get_current_active_user)
) -> ComplianceCheckResponse:
    """
    Check data compliance against policies.

    **Required:** Authenticated user

    Checks data against all enabled policies or specific policies if provided.
    """
    try:
        engine = get_policy_engine()

        result = engine.check_compliance(
            data=request.data,
            policy_names=request.policy_names
        )

        return ComplianceCheckResponse(**result)

    except Exception as e:
        logger.error(f"Failed to check compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/violations", response_model=ViolationListResponse, summary="Get Violations")
async def get_violations(
    severity: Optional[str] = QueryParam(None, pattern="^(info|warning|error|critical)$"),
    limit: int = QueryParam(100, ge=1, le=1000),
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> ViolationListResponse:
    """
    Get recent policy violations.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()
        violations = engine.get_violations(severity=severity, limit=limit)

        violation_responses = [
            ViolationResponse(
                policy_name=v.policy_name,
                severity=v.severity.value,
                description=v.description,
                data_context=v.data_context,
                timestamp=v.timestamp.isoformat(),
                metadata=v.metadata
            )
            for v in violations
        ]

        return ViolationListResponse(
            violations=violation_responses,
            total=len(violation_responses)
        )

    except Exception as e:
        logger.error(f"Failed to get violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/violations", summary="Clear Violations")
async def clear_violations(
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> Dict[str, str]:
    """
    Clear all recorded violations.

    **Required Permission:** `admin:system`
    """
    try:
        engine = get_policy_engine()
        engine.clear_violations()

        return {"message": "All violations cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ComplianceStatsResponse, summary="Get Compliance Statistics")
async def get_compliance_stats(
    current_user: User = Depends(PermissionChecker("admin:system"))
) -> ComplianceStatsResponse:
    """
    Get compliance system statistics.

    **Required Permission:** `admin:system`
    """
    try:
        policy_engine = get_policy_engine()
        compliance_engine = get_compliance_engine()

        policy_stats = policy_engine.get_statistics()
        compliance_stats = compliance_engine.get_statistics()

        return ComplianceStatsResponse(
            total_policies=policy_stats["total_policies"],
            enabled_policies=policy_stats["enabled_policies"],
            disabled_policies=policy_stats["disabled_policies"],
            total_violations=policy_stats["total_violations"],
            violations_by_severity=policy_stats["violations_by_severity"],
            policies_by_type=policy_stats["policies_by_type"],
            presidio_enabled=compliance_stats["presidio_enabled"],
            supported_entities=compliance_stats["supported_entities"]
        )

    except Exception as e:
        logger.error(f"Failed to get compliance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
