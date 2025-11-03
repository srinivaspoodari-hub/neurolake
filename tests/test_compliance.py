"""
Tests for Compliance Module
"""

import pytest
from unittest.mock import Mock, patch

from neurolake.compliance import (
    ComplianceEngine,
    PolicyEngine,
    DataMasker,
    AuditLogger,
    PIIResult,
    Policy,
    PolicyViolation,
    MaskingStrategy,
    MaskingConfig,
    AuditEvent
)
from neurolake.compliance.engine import PIIType
from neurolake.compliance.policy import PolicyType, PolicySeverity
from neurolake.compliance.audit import AuditEventType, AuditLevel


# ===== ComplianceEngine Tests =====

def test_compliance_engine_creation():
    """Test creating compliance engine."""
    engine = ComplianceEngine(use_presidio=False)

    assert engine is not None
    assert not engine.use_presidio
    assert len(engine._patterns) > 0


def test_detect_pii_email():
    """Test detecting email addresses."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Contact us at support@example.com"
    results = engine.detect_pii(text)

    assert len(results) > 0
    email_result = next(r for r in results if r.entity_type == PIIType.EMAIL)
    assert email_result.text == "support@example.com"


def test_detect_pii_phone():
    """Test detecting phone numbers."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Call me at 555-123-4567"
    results = engine.detect_pii(text)

    assert len(results) > 0
    phone_result = next((r for r in results if r.entity_type == PIIType.PHONE), None)
    assert phone_result is not None


def test_detect_pii_ssn():
    """Test detecting SSN."""
    engine = ComplianceEngine(use_presidio=False)

    text = "SSN: 123-45-6789"
    results = engine.detect_pii(text)

    assert len(results) > 0
    ssn_result = next((r for r in results if r.entity_type == PIIType.SSN), None)
    assert ssn_result is not None


def test_detect_pii_multiple():
    """Test detecting multiple PII types."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Email: john@example.com, Phone: 555-123-4567, SSN: 123-45-6789"
    results = engine.detect_pii(text)

    assert len(results) >= 2  # At least email and one other


def test_contains_pii():
    """Test checking if text contains PII."""
    engine = ComplianceEngine(use_presidio=False)

    assert engine.contains_pii("Email: test@example.com")
    assert not engine.contains_pii("This is plain text")


def test_get_pii_types():
    """Test getting PII types."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Email: test@example.com, Phone: 555-1234"
    types = engine.get_pii_types(text)

    assert PIIType.EMAIL in types


def test_mask_data():
    """Test masking PII data."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Email: test@example.com"
    masked = engine.mask_data(text)

    assert "test@example.com" not in masked
    assert "*" in masked


def test_anonymize_data():
    """Test anonymizing PII data."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Email: test@example.com"
    anonymized = engine.anonymize_data(text)

    assert "test@example.com" not in anonymized
    assert "<EMAIL>" in anonymized or "<URL>" in anonymized


def test_get_statistics():
    """Test getting compliance statistics."""
    engine = ComplianceEngine(use_presidio=False)

    stats = engine.get_statistics()

    assert "presidio_enabled" in stats
    assert "supported_entities" in stats
    assert stats["regex_patterns"] > 0


# ===== PolicyEngine Tests =====

def test_policy_engine_creation():
    """Test creating policy engine."""
    engine = PolicyEngine()

    assert engine is not None
    assert len(engine.policies) == 0


def test_add_policy():
    """Test adding a policy."""
    engine = PolicyEngine()

    def check_length(data):
        return len(str(data)) < 100

    policy = engine.add_policy(
        name="max_length",
        policy_type="custom",
        description="Max length 100",
        check_function=check_length
    )

    assert "max_length" in engine.policies
    assert policy.name == "max_length"


def test_policy_check():
    """Test policy checking."""
    engine = PolicyEngine()

    def no_numbers(data):
        return not any(c.isdigit() for c in str(data))

    engine.add_policy(
        name="no_numbers",
        policy_type="custom",
        description="No numbers allowed",
        check_function=no_numbers
    )

    result = engine.check_compliance("test data")
    assert result["compliant"]

    result = engine.check_compliance("test123")
    assert not result["compliant"]


def test_policy_severity():
    """Test policy severity levels."""
    engine = PolicyEngine()

    engine.add_policy(
        name="critical_policy",
        policy_type="custom",
        description="Critical",
        check_function=lambda x: False,
        severity="critical"
    )

    result = engine.check_compliance("test")

    assert not result["compliant"]
    assert len(result["violations"]) > 0
    assert result["violations"][0]["severity"] == "critical"


def test_enable_disable_policy():
    """Test enabling/disabling policies."""
    engine = PolicyEngine()

    engine.add_policy(
        name="test_policy",
        policy_type="custom",
        description="Test",
        check_function=lambda x: False
    )

    # Should violate
    result = engine.check_compliance("test")
    assert not result["compliant"]

    # Disable
    engine.disable_policy("test_policy")
    result = engine.check_compliance("test")
    assert result["compliant"]

    # Re-enable
    engine.enable_policy("test_policy")
    result = engine.check_compliance("test")
    assert not result["compliant"]


def test_list_policies():
    """Test listing policies."""
    engine = PolicyEngine()

    engine.add_policy("p1", "custom", "Policy 1", lambda x: True)
    engine.add_policy("p2", "pii_protection", "Policy 2", lambda x: True)
    engine.add_policy("p3", "custom", "Policy 3", lambda x: True)

    all_policies = engine.list_policies()
    assert len(all_policies) == 3

    custom_policies = engine.list_policies(policy_type="custom")
    assert len(custom_policies) == 2


def test_builtin_policies():
    """Test built-in policies."""
    compliance_engine = ComplianceEngine(use_presidio=False)
    policy_engine = PolicyEngine()

    policy_engine.add_builtin_policies(compliance_engine)

    assert "no_pii" in policy_engine.policies
    assert "no_empty_data" in policy_engine.policies


def test_get_violations():
    """Test getting violations."""
    engine = PolicyEngine()

    engine.add_policy(
        name="always_fail",
        policy_type="custom",
        description="Test",
        check_function=lambda x: False
    )

    engine.check_compliance("test1")
    engine.check_compliance("test2")

    violations = engine.get_violations()
    assert len(violations) >= 2


def test_policy_statistics():
    """Test policy statistics."""
    engine = PolicyEngine()

    engine.add_policy("p1", "custom", "Test", lambda x: True)
    engine.add_policy("p2", "pii_protection", "Test", lambda x: False)

    stats = engine.get_statistics()

    assert stats["total_policies"] == 2
    assert stats["enabled_policies"] == 2


# ===== DataMasker Tests =====

def test_data_masker_creation():
    """Test creating data masker."""
    masker = DataMasker()

    assert masker is not None
    assert masker.salt is not None


def test_mask_redact():
    """Test redaction masking."""
    masker = DataMasker()

    masked = masker.mask("sensitive", strategy="redact")

    assert masked == "*********"


def test_mask_hash():
    """Test hash masking."""
    masker = DataMasker()

    masked = masker.mask("test@example.com", strategy="hash")

    assert len(masked) == 64  # SHA256 hex length
    assert masked != "test@example.com"


def test_mask_partial():
    """Test partial masking."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.PARTIAL,
        partial_reveal_end=4
    )

    masked = masker.mask("1234567890", config=config)

    assert masked.endswith("7890")
    assert "*" in masked


def test_mask_tokenize():
    """Test tokenization."""
    masker = DataMasker()

    token1 = masker.mask("sensitive1", strategy="tokenize")
    token2 = masker.mask("sensitive2", strategy="tokenize")
    token3 = masker.mask("sensitive1", strategy="tokenize")

    assert token1 != token2
    assert token1 == token3  # Same input -> same token


def test_mask_pii_result():
    """Test masking PII result."""
    masker = DataMasker()

    text = "Email: test@example.com"
    pii_result = PIIResult(
        entity_type=PIIType.EMAIL,
        text="test@example.com",
        start=7,
        end=23,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)

    assert "test@example.com" not in masked


def test_mask_multiple():
    """Test masking multiple entities."""
    masker = DataMasker()

    text = "Email: test@example.com, Phone: 555-1234"
    pii_results = [
        PIIResult(PIIType.EMAIL, "test@example.com", 7, 23, 0.9),
        PIIResult(PIIType.PHONE, "555-1234", 32, 40, 0.8)
    ]

    masked = masker.mask_multiple(text, pii_results)

    assert "test@example.com" not in masked
    assert "555-1234" not in masked


def test_masking_presets():
    """Test masking presets."""
    from neurolake.compliance.masking import MaskingPresets

    cc_config = MaskingPresets.credit_card()
    assert cc_config.strategy == MaskingStrategy.PARTIAL
    assert cc_config.partial_reveal_end == 4

    ssn_config = MaskingPresets.ssn()
    assert ssn_config.strategy == MaskingStrategy.PARTIAL


# ===== AuditLogger Tests =====

def test_audit_logger_creation():
    """Test creating audit logger."""
    logger = AuditLogger()

    assert logger is not None
    assert len(logger.events) == 0


def test_log_access():
    """Test logging data access."""
    logger = AuditLogger()

    event = logger.log_access(
        resource="users_table",
        action="SELECT",
        user="john@example.com"
    )

    assert event.event_type == AuditEventType.DATA_ACCESS
    assert event.resource == "users_table"
    assert event.action == "SELECT"
    assert len(logger.events) == 1


def test_log_query():
    """Test logging query execution."""
    logger = AuditLogger()

    event = logger.log_query(
        query="SELECT * FROM users",
        user="analyst@example.com",
        table="users",
        rows_returned=100
    )

    assert event.event_type == AuditEventType.DATA_QUERY
    assert event.metadata["rows_returned"] == 100


def test_log_pii_detection():
    """Test logging PII detection."""
    logger = AuditLogger()

    event = logger.log_pii_detection(
        text="Found email",
        pii_count=1,
        pii_types=["EMAIL"],
        user="user@example.com"
    )

    assert event.event_type == AuditEventType.PII_DETECTION
    assert event.metadata["pii_count"] == 1


def test_log_violation():
    """Test logging policy violation."""
    logger = AuditLogger()

    event = logger.log_violation(
        policy_name="no_pii",
        severity="critical",
        details="PII detected",
        user="user@example.com"
    )

    assert event.event_type == AuditEventType.POLICY_VIOLATION
    assert event.status == "violation"


def test_log_masking():
    """Test logging masking event."""
    logger = AuditLogger()

    event = logger.log_masking(
        strategy="redact",
        entity_count=5,
        user="user@example.com"
    )

    assert event.event_type == AuditEventType.MASKING_APPLIED
    assert event.metadata["entity_count"] == 5


def test_log_export():
    """Test logging data export."""
    logger = AuditLogger()

    event = logger.log_export(
        destination="export.csv",
        record_count=1000,
        user="user@example.com",
        format="csv"
    )

    assert event.event_type == AuditEventType.DATA_EXPORT
    assert event.metadata["record_count"] == 1000


def test_get_events():
    """Test getting filtered events."""
    logger = AuditLogger()

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user2")
    logger.log_query("SELECT 1", user="user1")

    # Get all events
    all_events = logger.get_events()
    assert len(all_events) == 3

    # Filter by user
    user1_events = logger.get_events(user="user1")
    assert len(user1_events) == 2

    # Filter by event type
    access_events = logger.get_events(event_type="data_access")
    assert len(access_events) == 2


def test_audit_statistics():
    """Test audit statistics."""
    logger = AuditLogger()

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user1")
    logger.log_query("SELECT 1", user="user2")

    stats = logger.get_statistics()

    assert stats["total_events"] == 3
    assert "events_by_type" in stats
    assert "top_users" in stats


# ===== Integration Tests =====

def test_full_compliance_flow():
    """Test complete compliance flow."""
    # Create components
    compliance_engine = ComplianceEngine(use_presidio=False)
    policy_engine = PolicyEngine()
    masker = DataMasker()
    audit_logger = AuditLogger()

    # Add policies
    policy_engine.add_builtin_policies(compliance_engine)

    # Test data with PII
    text = "User email is john@example.com and phone is 555-1234"

    # 1. Detect PII
    pii_results = compliance_engine.detect_pii(text)
    audit_logger.log_pii_detection(
        text=text,
        pii_count=len(pii_results),
        user="analyst@example.com"
    )

    assert len(pii_results) > 0

    # 2. Check policies
    result = policy_engine.check_compliance(text)

    if not result["compliant"]:
        for violation in result["violations"]:
            audit_logger.log_violation(
                policy_name=violation["policy_name"],
                severity=violation["severity"],
                details=violation["description"],
                user="analyst@example.com"
            )

    # 3. Mask data
    masked_text = masker.mask_multiple(text, pii_results)
    audit_logger.log_masking(
        strategy="redact",
        entity_count=len(pii_results),
        user="analyst@example.com"
    )

    assert "john@example.com" not in masked_text

    # 4. Verify audit trail
    events = audit_logger.get_events()
    assert len(events) >= 2  # At least PII detection and masking


def test_compliance_with_clean_data():
    """Test compliance with data that has no PII."""
    compliance_engine = ComplianceEngine(use_presidio=False)
    policy_engine = PolicyEngine()
    policy_engine.add_builtin_policies(compliance_engine)

    clean_text = "This is a clean text without any sensitive information"

    # Should have no PII
    pii_results = compliance_engine.detect_pii(clean_text)
    assert len(pii_results) == 0

    # Should pass policies
    result = policy_engine.check_compliance(clean_text)
    assert result["compliant"]


def test_end_to_end_query_compliance():
    """Test end-to-end query compliance checking."""
    # Setup
    compliance_engine = ComplianceEngine(use_presidio=False)
    policy_engine = PolicyEngine()
    audit_logger = AuditLogger()

    policy_engine.add_builtin_policies(compliance_engine)

    # Simulate user query with PII
    query = "SELECT * FROM users WHERE email = 'test@example.com'"

    # Log query
    audit_logger.log_query(
        query=query,
        user="analyst@example.com",
        table="users"
    )

    # Check for PII in query
    pii_results = compliance_engine.detect_pii(query)

    if pii_results:
        audit_logger.log_pii_detection(
            text=query,
            pii_count=len(pii_results),
            user="analyst@example.com"
        )

    # Check compliance
    result = policy_engine.check_compliance(query)

    # Verify audit trail
    events = audit_logger.get_events()
    assert len(events) >= 1


# ===== Additional Coverage Tests =====

def test_policy_enforce_raises_exception():
    """Test enforce_policies raises exception."""
    from neurolake.compliance.policy import PolicyViolationError

    engine = PolicyEngine()

    engine.add_policy(
        name="always_fail",
        policy_type="custom",
        description="Test",
        check_function=lambda x: False
    )

    with pytest.raises(PolicyViolationError):
        engine.enforce_policies("test", raise_on_violation=True)


def test_policy_enforce_no_raise():
    """Test enforce_policies without raising exception."""
    engine = PolicyEngine()

    engine.add_policy(
        name="always_fail",
        policy_type="custom",
        description="Test",
        check_function=lambda x: False
    )

    result = engine.enforce_policies("test", raise_on_violation=False)
    assert result is False


def test_mask_hash_md5():
    """Test MD5 hashing."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.HASH,
        hash_algorithm="md5"
    )

    masked = masker.mask("test", config=config)
    assert len(masked) == 32  # MD5 hex length


def test_mask_hash_sha1():
    """Test SHA1 hashing."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.HASH,
        hash_algorithm="sha1"
    )

    masked = masker.mask("test", config=config)
    assert len(masked) == 40  # SHA1 hex length


def test_mask_synthetic_phone():
    """Test synthetic data generation for phone."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.SYNTHETIC)
    masked = masker.mask("555-123-4567", config=config)

    assert masked != "555-123-4567"
    assert "-" in masked


def test_mask_synthetic_digits():
    """Test synthetic data generation for digits."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.SYNTHETIC)
    masked = masker.mask("12345", config=config)

    assert masked != "12345"
    assert masked.isdigit()


def test_mask_synthetic_text():
    """Test synthetic data generation for text."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.SYNTHETIC)
    masked = masker.mask("hello", config=config)

    assert masked != "hello"
    assert len(masked) == 5


def test_mask_null():
    """Test NULL masking strategy."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.NULL)
    masked = masker.mask("anything", config=config)

    assert masked == "NULL"


def test_mask_encrypt():
    """Test ENCRYPT masking strategy (falls back to redact)."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.ENCRYPT)
    masked = masker.mask("test", config=config)

    # Currently falls back to redact
    assert "*" in masked


def test_mask_redact_no_preserve_length():
    """Test redaction without preserving length."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.REDACT,
        preserve_length=False
    )

    masked = masker.mask("verylongtext", config=config)
    assert masked == "********"


def test_clear_tokens():
    """Test clearing token mapping."""
    masker = DataMasker()

    masker.mask("test1", strategy="tokenize")
    masker.mask("test2", strategy="tokenize")

    assert len(masker.get_token_mapping()) == 2

    masker.clear_tokens()
    assert len(masker.get_token_mapping()) == 0


def test_audit_logger_with_file(tmp_path):
    """Test audit logger with file output."""
    log_file = tmp_path / "audit.log"

    logger = AuditLogger(log_file=str(log_file))

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user2")

    # Check file exists
    assert log_file.exists()

    # Read file content
    content = log_file.read_text()
    assert "table1" in content
    assert "table2" in content


def test_audit_flush(tmp_path):
    """Test flushing audit log to file."""
    log_file = tmp_path / "audit_flush.log"

    logger = AuditLogger(log_file=str(log_file), auto_flush=False)

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user2")

    # Flush manually
    logger.flush()

    # Check file exists and has content
    assert log_file.exists()
    content = log_file.read_text()
    assert "table1" in content


def test_audit_export_json(tmp_path):
    """Test exporting audit log to JSON."""
    output_file = tmp_path / "export.json"

    logger = AuditLogger()
    logger.log_access("table1", "SELECT", "user1")

    logger.export_events(str(output_file), format="json")

    assert output_file.exists()
    content = output_file.read_text()
    assert "table1" in content


def test_audit_export_csv(tmp_path):
    """Test exporting audit log to CSV."""
    output_file = tmp_path / "export.csv"

    logger = AuditLogger()
    logger.log_access("table1", "SELECT", "user1")

    logger.export_events(str(output_file), format="csv")

    assert output_file.exists()
    content = output_file.read_text()
    assert "table1" in content


def test_audit_clear_events():
    """Test clearing audit events."""
    logger = AuditLogger()

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user2")

    assert len(logger.events) == 2

    logger.clear_events()
    assert len(logger.events) == 0


def test_audit_get_events_by_level():
    """Test filtering events by level."""
    logger = AuditLogger()

    logger.log_access("table1", "SELECT", "user1")
    logger.log_violation("policy1", "critical", "Test", "user1")

    critical_events = logger.get_events(level="critical")
    assert len(critical_events) >= 1


def test_compliance_engine_with_presidio_enabled():
    """Test creating engine with Presidio enabled (will fail gracefully)."""
    # This tests the Presidio initialization path
    try:
        engine = ComplianceEngine(use_presidio=True)
        # May or may not have Presidio installed
        # Just verify engine is created
        assert engine is not None
    except (OSError, ImportError):
        # Presidio dependencies may fail to load on some systems
        pytest.skip("Presidio dependencies not available")


def test_pii_result_to_dict():
    """Test PIIResult to_dict conversion."""
    result = PIIResult(
        entity_type=PIIType.EMAIL,
        text="test@example.com",
        start=0,
        end=16,
        confidence=0.9,
        context="test context",
        metadata={"key": "value"}
    )

    result_dict = result.to_dict()

    assert result_dict["entity_type"] == "email"
    assert result_dict["text"] == "test@example.com"
    assert result_dict["confidence"] == 0.9


def test_policy_to_dict():
    """Test Policy to_dict conversion."""
    policy = Policy(
        name="test_policy",
        policy_type=PolicyType.CUSTOM,
        description="Test policy",
        check_function=lambda x: True,
        severity=PolicySeverity.WARNING
    )

    policy_dict = policy.to_dict()

    assert policy_dict["name"] == "test_policy"
    assert policy_dict["policy_type"] == "custom"
    assert policy_dict["severity"] == "warning"


def test_policy_violation_to_dict():
    """Test PolicyViolation to_dict conversion."""
    from neurolake.compliance.policy import PolicyViolation, PolicySeverity

    violation = PolicyViolation(
        policy_name="test_policy",
        severity=PolicySeverity.ERROR,
        description="Test violation",
        data_context="test data"
    )

    violation_dict = violation.to_dict()

    assert violation_dict["policy_name"] == "test_policy"
    assert violation_dict["severity"] == "error"


def test_audit_event_to_json():
    """Test AuditEvent to_json conversion."""
    from neurolake.compliance.audit import AuditEvent, AuditEventType, AuditLevel

    event = AuditEvent(
        event_type=AuditEventType.DATA_ACCESS,
        level=AuditLevel.INFO,
        message="Test event",
        user="test_user"
    )

    json_str = event.to_json()

    assert "Test event" in json_str
    assert "test_user" in json_str


def test_policy_check_with_context():
    """Test policy checking with context."""
    engine = PolicyEngine()

    def check_with_context(data, context=None):
        if context is None:
            return False
        return context.get("allowed", False)

    engine.add_policy(
        name="context_policy",
        policy_type="custom",
        description="Uses context",
        check_function=check_with_context
    )

    # Should fail without context
    result = engine.check_compliance("test")
    assert not result["compliant"]

    # Should pass with context
    result = engine.check_compliance("test", context={"allowed": True})
    assert result["compliant"]


def test_policy_check_exception_handling():
    """Test policy check handles exceptions."""
    engine = PolicyEngine()

    def failing_check(data):
        raise ValueError("Test error")

    engine.add_policy(
        name="failing_policy",
        policy_type="custom",
        description="Fails",
        check_function=failing_check
    )

    # Should not raise, just return False
    result = engine.check_compliance("test")
    assert not result["compliant"]


def test_get_pii_types_empty():
    """Test get_pii_types with no PII."""
    engine = ComplianceEngine(use_presidio=False)

    types = engine.get_pii_types("plain text")
    assert len(types) == 0


def test_mask_partial_too_short():
    """Test partial masking with text too short."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.PARTIAL,
        partial_reveal_start=5,
        partial_reveal_end=5
    )

    # Text shorter than reveal requirements
    masked = masker.mask("ab", config=config)
    assert masked == "ab"  # Should return unchanged


def test_detect_pii_empty_text():
    """Test PII detection with empty text."""
    engine = ComplianceEngine(use_presidio=False)

    results = engine.detect_pii("")
    assert len(results) == 0


def test_mask_data_no_pii():
    """Test masking data with no PII."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Plain text without PII"
    masked = engine.mask_data(text)

    assert masked == text  # Should be unchanged


def test_anonymize_data_no_pii():
    """Test anonymizing data with no PII."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Plain text without PII"
    anonymized = engine.anonymize_data(text)

    assert anonymized == text  # Should be unchanged


def test_detect_pii_ip_address():
    """Test detecting IP addresses."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Server at 192.168.1.1"
    results = engine.detect_pii(text)

    ip_result = next((r for r in results if r.entity_type == PIIType.IP_ADDRESS), None)
    assert ip_result is not None
    assert "192.168.1.1" in ip_result.text


def test_detect_pii_url():
    """Test detecting URLs."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Visit https://example.com for more info"
    results = engine.detect_pii(text)

    url_result = next((r for r in results if r.entity_type == PIIType.URL), None)
    assert url_result is not None


def test_detect_pii_credit_card():
    """Test detecting credit cards."""
    engine = ComplianceEngine(use_presidio=False)

    text = "Card: 4532-1234-5678-9010"
    results = engine.detect_pii(text)

    cc_result = next((r for r in results if r.entity_type == PIIType.CREDIT_CARD), None)
    assert cc_result is not None


def test_mask_shuffle():
    """Test shuffle masking strategy."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.SHUFFLE)
    masked = masker.mask("abcdefgh", config=config)

    # Shuffled should be different (with high probability)
    # but have same length and characters
    assert len(masked) == 8
    assert sorted(masked) == sorted("abcdefgh")


def test_mask_synthetic_email():
    """Test synthetic data generation for email."""
    masker = DataMasker()

    config = MaskingConfig(strategy=MaskingStrategy.SYNTHETIC)
    masked = masker.mask("john@example.com", config=config)

    assert masked != "john@example.com"
    assert "@" in masked
    assert "example.com" in masked


def test_mask_dataframe_column():
    """Test masking DataFrame column."""
    try:
        import pandas as pd
    except ImportError:
        pytest.skip("Pandas not installed")

    masker = DataMasker()

    df = pd.DataFrame({
        'email': ['test@example.com', 'user@test.com'],
        'name': ['John', 'Jane']
    })

    masked_df = masker.mask_dataframe_column(df.copy(), 'email', strategy='redact')

    assert 'test@example.com' not in masked_df['email'].values
    assert '*' in masked_df['email'].values[0]


def test_policy_with_specific_policies():
    """Test checking compliance with specific policies."""
    engine = PolicyEngine()

    engine.add_policy("p1", "custom", "Test 1", lambda x: True)
    engine.add_policy("p2", "custom", "Test 2", lambda x: False)
    engine.add_policy("p3", "custom", "Test 3", lambda x: False)

    # Check only p1
    result = engine.check_compliance("test", policy_names=["p1"])
    assert result["compliant"]

    # Check only p2
    result = engine.check_compliance("test", policy_names=["p2"])
    assert not result["compliant"]


def test_policy_remove():
    """Test removing a policy."""
    engine = PolicyEngine()

    engine.add_policy("test_policy", "custom", "Test", lambda x: True)
    assert "test_policy" in engine.policies

    engine.remove_policy("test_policy")
    assert "test_policy" not in engine.policies


def test_policy_get():
    """Test getting a policy."""
    engine = PolicyEngine()

    policy = engine.add_policy("test_policy", "custom", "Test", lambda x: True)

    retrieved = engine.get_policy("test_policy")
    assert retrieved == policy

    none_policy = engine.get_policy("nonexistent")
    assert none_policy is None


def test_policy_clear_violations():
    """Test clearing violations."""
    engine = PolicyEngine()

    engine.add_policy("always_fail", "custom", "Test", lambda x: False)

    engine.check_compliance("test1")
    engine.check_compliance("test2")

    assert len(engine.violations) >= 2

    engine.clear_violations()
    assert len(engine.violations) == 0


def test_policy_get_violations_by_severity():
    """Test getting violations by severity."""
    engine = PolicyEngine()

    engine.add_policy("critical_policy", "custom", "Test", lambda x: False, severity="critical")
    engine.add_policy("warning_policy", "custom", "Test", lambda x: False, severity="warning")

    engine.check_compliance("test")

    critical_violations = engine.get_violations(severity="critical")
    warning_violations = engine.get_violations(severity="warning")

    assert len(critical_violations) >= 1
    assert len(warning_violations) >= 1


def test_policy_list_enabled_only():
    """Test listing only enabled policies."""
    engine = PolicyEngine()

    engine.add_policy("p1", "custom", "Test 1", lambda x: True)
    engine.add_policy("p2", "custom", "Test 2", lambda x: True)

    engine.disable_policy("p2")

    enabled = engine.list_policies(enabled_only=True)
    assert len(enabled) == 1


def test_audit_get_events_by_resource():
    """Test filtering events by resource."""
    logger = AuditLogger()

    logger.log_access("table1", "SELECT", "user1")
    logger.log_access("table2", "INSERT", "user2")

    table1_events = logger.get_events(resource="table1")
    assert len(table1_events) == 1
    assert table1_events[0].resource == "table1"


def test_audit_max_events():
    """Test max events limit."""
    logger = AuditLogger(max_events=5)

    for i in range(10):
        logger.log_access(f"table{i}", "SELECT", "user1")

    # Should only keep last 5
    assert len(logger.events) == 5


def test_mask_default_config_for_pii_types():
    """Test default masking configs for different PII types."""
    masker = DataMasker()

    # Test different PII types get appropriate defaults
    text = "Card: 1234-5678-9012-3456"
    pii_result = PIIResult(
        entity_type=PIIType.CREDIT_CARD,
        text="1234-5678-9012-3456",
        start=6,
        end=25,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)
    # Credit card should show last 4
    assert "3456" in masked


def test_mask_default_config_ssn():
    """Test default masking config for SSN."""
    masker = DataMasker()

    text = "SSN: 123-45-6789"
    pii_result = PIIResult(
        entity_type=PIIType.SSN,
        text="123-45-6789",
        start=5,
        end=16,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)
    # SSN should show last 4
    assert "6789" in masked


def test_mask_default_config_phone():
    """Test default masking config for phone."""
    masker = DataMasker()

    text = "Phone: 555-123-4567"
    pii_result = PIIResult(
        entity_type=PIIType.PHONE,
        text="555-123-4567",
        start=7,
        end=19,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)
    # Phone should show last 4
    assert "4567" in masked


def test_mask_default_config_email():
    """Test default masking config for email (hash)."""
    masker = DataMasker()

    text = "Email: test@example.com"
    pii_result = PIIResult(
        entity_type=PIIType.EMAIL,
        text="test@example.com",
        start=7,
        end=23,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)
    # Email should be hashed
    assert "test@example.com" not in masked
    assert len(masked) > 50  # Hash is long


def test_mask_default_config_other():
    """Test default masking config for other PII types."""
    masker = DataMasker()

    text = "Address: 123 Main St"
    pii_result = PIIResult(
        entity_type=PIIType.ADDRESS,
        text="123 Main St",
        start=9,
        end=20,
        confidence=0.9
    )

    masked = masker.mask_pii_result(pii_result, text)
    # Other types should be redacted
    assert "123 Main St" not in masked
    assert "*" in masked


def test_partial_mask_with_start_and_end():
    """Test partial masking with both start and end reveal."""
    masker = DataMasker()

    config = MaskingConfig(
        strategy=MaskingStrategy.PARTIAL,
        partial_reveal_start=2,
        partial_reveal_end=2
    )

    masked = masker.mask("1234567890", config=config)

    assert masked.startswith("12")
    assert masked.endswith("90")
    assert "*" in masked


def test_audit_event_to_dict():
    """Test AuditEvent to_dict conversion."""
    from neurolake.compliance.audit import AuditEvent, AuditEventType, AuditLevel

    event = AuditEvent(
        event_type=AuditEventType.DATA_ACCESS,
        level=AuditLevel.INFO,
        message="Test event",
        user="test_user",
        resource="test_table",
        action="SELECT",
        status="success"
    )

    event_dict = event.to_dict()

    assert event_dict["event_type"] == "data_access"
    assert event_dict["level"] == "info"
    assert event_dict["user"] == "test_user"
    assert event_dict["resource"] == "test_table"


def test_policy_disabled_check():
    """Test that disabled policies are not checked."""
    policy = Policy(
        name="test_policy",
        policy_type=PolicyType.CUSTOM,
        description="Test",
        check_function=lambda x: False,  # Would fail
        enabled=False  # But disabled
    )

    # Should return True because disabled
    result = policy.check("test data")
    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
