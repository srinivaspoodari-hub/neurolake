"""
Compliance Engine

Main engine for PII detection and compliance operations.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_LICENSE = "medical_license"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account"
    IBAN = "iban"
    URL = "url"
    CUSTOM = "custom"


@dataclass
class PIIResult:
    """Result of PII detection."""
    entity_type: PIIType
    text: str
    start: int
    end: int
    confidence: float
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_type": self.entity_type.value,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "context": self.context,
            "metadata": self.metadata
        }


class ComplianceEngine:
    """
    Main compliance engine for PII detection and data protection.

    Example:
        engine = ComplianceEngine()

        # Detect PII
        text = "Contact John at john@example.com or 555-1234"
        results = engine.detect_pii(text)

        # Mask PII
        masked = engine.mask_data(text, results)

        # Check if text contains PII
        has_pii = engine.contains_pii(text)
    """

    def __init__(
        self,
        use_presidio: bool = True,
        supported_entities: Optional[List[str]] = None
    ):
        """
        Initialize compliance engine.

        Args:
            use_presidio: Whether to use Presidio for detection
            supported_entities: List of entity types to detect
        """
        self.use_presidio = use_presidio
        self.supported_entities = supported_entities or [
            "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
            "US_SSN", "IP_ADDRESS", "PERSON", "LOCATION",
            "DATE_TIME", "MEDICAL_LICENSE", "US_PASSPORT",
            "US_DRIVER_LICENSE", "US_BANK_NUMBER", "IBAN_CODE",
            "URL"
        ]

        # Presidio components
        self.analyzer = None
        self.anonymizer = None

        # Initialize Presidio if available
        if self.use_presidio:
            self._init_presidio()

        # Regex patterns for fallback detection
        self._patterns = self._build_regex_patterns()

    def _init_presidio(self):
        """Initialize Presidio analyzer and anonymizer."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine

            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio initialized successfully")

        except ImportError:
            logger.warning(
                "Presidio not installed. Install with: "
                "pip install presidio-analyzer presidio-anonymizer"
            )
            self.use_presidio = False

    def _build_regex_patterns(self) -> Dict[PIIType, re.Pattern]:
        """Build regex patterns for PII detection."""
        return {
            PIIType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            PIIType.PHONE: re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            ),
            PIIType.SSN: re.compile(
                r'\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b'
            ),
            PIIType.CREDIT_CARD: re.compile(
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
            ),
            PIIType.IP_ADDRESS: re.compile(
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            ),
            PIIType.URL: re.compile(
                r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
            ),
        }

    def detect_pii(
        self,
        text: str,
        language: str = "en",
        entities: Optional[List[str]] = None,
        threshold: float = 0.5
    ) -> List[PIIResult]:
        """
        Detect PII in text.

        Args:
            text: Text to analyze
            language: Language code
            entities: Specific entities to detect
            threshold: Confidence threshold

        Returns:
            List of PII detection results
        """
        if not text:
            return []

        # Use Presidio if available
        if self.use_presidio and self.analyzer:
            return self._detect_pii_presidio(text, language, entities, threshold)

        # Fallback to regex patterns
        return self._detect_pii_regex(text, threshold)

    def _detect_pii_presidio(
        self,
        text: str,
        language: str,
        entities: Optional[List[str]],
        threshold: float
    ) -> List[PIIResult]:
        """Detect PII using Presidio."""
        entities_to_detect = entities or self.supported_entities

        # Analyze text
        results = self.analyzer.analyze(
            text=text,
            language=language,
            entities=entities_to_detect,
            score_threshold=threshold
        )

        # Convert to PIIResult
        pii_results = []
        for result in results:
            entity_type = self._map_presidio_entity(result.entity_type)
            pii_results.append(PIIResult(
                entity_type=entity_type,
                text=text[result.start:result.end],
                start=result.start,
                end=result.end,
                confidence=result.score,
                metadata={"presidio_type": result.entity_type}
            ))

        return pii_results

    def _detect_pii_regex(
        self,
        text: str,
        threshold: float
    ) -> List[PIIResult]:
        """Detect PII using regex patterns."""
        results = []

        for pii_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                results.append(PIIResult(
                    entity_type=pii_type,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,  # Fixed confidence for regex
                    metadata={"method": "regex"}
                ))

        return results

    def _map_presidio_entity(self, entity_type: str) -> PIIType:
        """Map Presidio entity type to PIIType."""
        mapping = {
            "EMAIL_ADDRESS": PIIType.EMAIL,
            "PHONE_NUMBER": PIIType.PHONE,
            "US_SSN": PIIType.SSN,
            "CREDIT_CARD": PIIType.CREDIT_CARD,
            "IP_ADDRESS": PIIType.IP_ADDRESS,
            "PERSON": PIIType.PERSON_NAME,
            "LOCATION": PIIType.ADDRESS,
            "DATE_TIME": PIIType.DATE_OF_BIRTH,
            "MEDICAL_LICENSE": PIIType.MEDICAL_LICENSE,
            "US_PASSPORT": PIIType.PASSPORT,
            "US_DRIVER_LICENSE": PIIType.DRIVER_LICENSE,
            "US_BANK_NUMBER": PIIType.BANK_ACCOUNT,
            "IBAN_CODE": PIIType.IBAN,
            "URL": PIIType.URL,
        }
        return mapping.get(entity_type, PIIType.CUSTOM)

    def contains_pii(
        self,
        text: str,
        threshold: float = 0.5
    ) -> bool:
        """
        Check if text contains PII.

        Args:
            text: Text to check
            threshold: Confidence threshold

        Returns:
            True if PII detected
        """
        results = self.detect_pii(text, threshold=threshold)
        return len(results) > 0

    def get_pii_types(
        self,
        text: str,
        threshold: float = 0.5
    ) -> Set[PIIType]:
        """
        Get set of PII types found in text.

        Args:
            text: Text to analyze
            threshold: Confidence threshold

        Returns:
            Set of detected PII types
        """
        results = self.detect_pii(text, threshold=threshold)
        return {r.entity_type for r in results}

    def mask_data(
        self,
        text: str,
        pii_results: Optional[List[PIIResult]] = None,
        mask_char: str = "*"
    ) -> str:
        """
        Mask PII in text.

        Args:
            text: Text to mask
            pii_results: PII detection results (will detect if not provided)
            mask_char: Character to use for masking

        Returns:
            Masked text
        """
        if pii_results is None:
            pii_results = self.detect_pii(text)

        if not pii_results:
            return text

        # Sort by position (reverse to preserve indices)
        sorted_results = sorted(pii_results, key=lambda x: x.start, reverse=True)

        masked_text = text
        for result in sorted_results:
            masked_value = mask_char * len(result.text)
            masked_text = (
                masked_text[:result.start] +
                masked_value +
                masked_text[result.end:]
            )

        return masked_text

    def anonymize_data(
        self,
        text: str,
        pii_results: Optional[List[PIIResult]] = None
    ) -> str:
        """
        Anonymize PII with type labels.

        Args:
            text: Text to anonymize
            pii_results: PII detection results

        Returns:
            Anonymized text
        """
        if pii_results is None:
            pii_results = self.detect_pii(text)

        if not pii_results:
            return text

        # Sort by position (reverse)
        sorted_results = sorted(pii_results, key=lambda x: x.start, reverse=True)

        anonymized_text = text
        for result in sorted_results:
            placeholder = f"<{result.entity_type.value.upper()}>"
            anonymized_text = (
                anonymized_text[:result.start] +
                placeholder +
                anonymized_text[result.end:]
            )

        return anonymized_text

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compliance engine statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "presidio_enabled": self.use_presidio and self.analyzer is not None,
            "supported_entities": len(self.supported_entities),
            "regex_patterns": len(self._patterns),
            "entities": self.supported_entities
        }


__all__ = ["ComplianceEngine", "PIIResult", "PIIType"]
