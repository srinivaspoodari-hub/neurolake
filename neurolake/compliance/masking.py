"""
Data Masking

Advanced data masking and anonymization strategies.
"""

import logging
import hashlib
import random
import string
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from neurolake.compliance.engine import PIIType, PIIResult

logger = logging.getLogger(__name__)


class MaskingStrategy(Enum):
    """Data masking strategies."""
    REDACT = "redact"  # Replace with asterisks
    HASH = "hash"  # One-way hash
    ENCRYPT = "encrypt"  # Reversible encryption
    TOKENIZE = "tokenize"  # Replace with token
    PARTIAL = "partial"  # Show only partial (e.g., last 4 digits)
    SHUFFLE = "shuffle"  # Shuffle characters
    SYNTHETIC = "synthetic"  # Replace with synthetic data
    NULL = "null"  # Replace with NULL


@dataclass
class MaskingConfig:
    """Configuration for masking operations."""
    strategy: MaskingStrategy
    mask_char: str = "*"
    preserve_length: bool = True
    partial_reveal_start: int = 0
    partial_reveal_end: int = 0
    hash_algorithm: str = "sha256"
    salt: Optional[str] = None


class DataMasker:
    """
    Advanced data masking engine.

    Example:
        masker = DataMasker()

        # Redact PII
        masked = masker.mask("SSN: 123-45-6789", strategy="redact")

        # Partial masking (show last 4)
        config = MaskingConfig(
            strategy=MaskingStrategy.PARTIAL,
            partial_reveal_end=4
        )
        masked = masker.mask_pii_result(pii_result, config)

        # Hash for consistency
        hashed = masker.mask("john@example.com", strategy="hash")
    """

    def __init__(self, salt: Optional[str] = None):
        """
        Initialize data masker.

        Args:
            salt: Salt for hashing
        """
        self.salt = salt or self._generate_salt()
        self._token_map: Dict[str, str] = {}

    def _generate_salt(self) -> str:
        """Generate random salt."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    def mask(
        self,
        data: str,
        strategy: str = "redact",
        config: Optional[MaskingConfig] = None
    ) -> str:
        """
        Mask data using specified strategy.

        Args:
            data: Data to mask
            strategy: Masking strategy
            config: Optional masking configuration

        Returns:
            Masked data
        """
        if not data:
            return data

        if config is None:
            config = MaskingConfig(
                strategy=MaskingStrategy[strategy.upper()]
            )

        strategy_enum = config.strategy

        if strategy_enum == MaskingStrategy.REDACT:
            return self._redact(data, config)
        elif strategy_enum == MaskingStrategy.HASH:
            return self._hash(data, config)
        elif strategy_enum == MaskingStrategy.PARTIAL:
            return self._partial_mask(data, config)
        elif strategy_enum == MaskingStrategy.SHUFFLE:
            return self._shuffle(data)
        elif strategy_enum == MaskingStrategy.TOKENIZE:
            return self._tokenize(data)
        elif strategy_enum == MaskingStrategy.NULL:
            return "NULL"
        elif strategy_enum == MaskingStrategy.SYNTHETIC:
            return self._generate_synthetic(data)
        else:
            return self._redact(data, config)

    def _redact(self, data: str, config: MaskingConfig) -> str:
        """Redact data with mask character."""
        if config.preserve_length:
            return config.mask_char * len(data)
        else:
            return config.mask_char * 8

    def _hash(self, data: str, config: MaskingConfig) -> str:
        """Hash data with salt."""
        algorithm = config.hash_algorithm
        salt = config.salt or self.salt

        salted_data = f"{data}{salt}"

        if algorithm == "sha256":
            return hashlib.sha256(salted_data.encode()).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(salted_data.encode()).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(salted_data.encode()).hexdigest()
        else:
            return hashlib.sha256(salted_data.encode()).hexdigest()

    def _partial_mask(self, data: str, config: MaskingConfig) -> str:
        """Partially mask data, revealing start/end."""
        reveal_start = config.partial_reveal_start
        reveal_end = config.partial_reveal_end

        if len(data) <= reveal_start + reveal_end:
            return data  # Too short to mask

        start_part = data[:reveal_start] if reveal_start > 0 else ""
        end_part = data[-reveal_end:] if reveal_end > 0 else ""
        middle_length = len(data) - reveal_start - reveal_end

        return start_part + (config.mask_char * middle_length) + end_part

    def _shuffle(self, data: str) -> str:
        """Shuffle characters."""
        chars = list(data)
        random.shuffle(chars)
        return ''.join(chars)

    def _tokenize(self, data: str) -> str:
        """Replace with consistent token."""
        if data in self._token_map:
            return self._token_map[data]

        token = f"TOKEN_{len(self._token_map) + 1:06d}"
        self._token_map[data] = token
        return token

    def _generate_synthetic(self, data: str) -> str:
        """Generate synthetic replacement data."""
        # Simple synthetic generation
        if "@" in data:
            # Email
            return f"user{random.randint(1000, 9999)}@example.com"
        elif data.replace("-", "").replace(" ", "").isdigit():
            # Phone or SSN
            if len(data) >= 10:
                return f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            else:
                return ''.join([str(random.randint(0, 9)) for _ in range(len(data))])
        else:
            # Generic text
            return ''.join(random.choices(string.ascii_letters, k=len(data)))

    def mask_pii_result(
        self,
        pii_result: PIIResult,
        text: str,
        config: Optional[MaskingConfig] = None
    ) -> str:
        """
        Mask specific PII result in text.

        Args:
            pii_result: PII detection result
            text: Original text
            config: Masking configuration

        Returns:
            Text with PII masked
        """
        if config is None:
            # Default configs by PII type
            config = self._get_default_config(pii_result.entity_type)

        masked_value = self.mask(pii_result.text, config=config)

        return (
            text[:pii_result.start] +
            masked_value +
            text[pii_result.end:]
        )

    def mask_multiple(
        self,
        text: str,
        pii_results: list,
        config: Optional[MaskingConfig] = None
    ) -> str:
        """
        Mask multiple PII entities in text.

        Args:
            text: Text to mask
            pii_results: List of PII detection results
            config: Masking configuration

        Returns:
            Masked text
        """
        # Sort by position (reverse to preserve indices)
        sorted_results = sorted(pii_results, key=lambda x: x.start, reverse=True)

        masked_text = text
        for result in sorted_results:
            entity_config = config or self._get_default_config(result.entity_type)
            masked_value = self.mask(result.text, config=entity_config)

            masked_text = (
                masked_text[:result.start] +
                masked_value +
                masked_text[result.end:]
            )

        return masked_text

    def _get_default_config(self, pii_type: PIIType) -> MaskingConfig:
        """Get default masking config for PII type."""
        if pii_type == PIIType.CREDIT_CARD:
            # Show last 4 digits
            return MaskingConfig(
                strategy=MaskingStrategy.PARTIAL,
                partial_reveal_end=4
            )
        elif pii_type == PIIType.SSN:
            # Show last 4
            return MaskingConfig(
                strategy=MaskingStrategy.PARTIAL,
                partial_reveal_end=4
            )
        elif pii_type == PIIType.EMAIL:
            # Hash for consistency
            return MaskingConfig(
                strategy=MaskingStrategy.HASH
            )
        elif pii_type == PIIType.PHONE:
            # Show last 4
            return MaskingConfig(
                strategy=MaskingStrategy.PARTIAL,
                partial_reveal_end=4
            )
        else:
            # Default redact
            return MaskingConfig(
                strategy=MaskingStrategy.REDACT
            )

    def mask_dataframe_column(
        self,
        df,
        column: str,
        strategy: str = "redact",
        config: Optional[MaskingConfig] = None
    ):
        """
        Mask a DataFrame column.

        Args:
            df: DataFrame
            column: Column name
            strategy: Masking strategy
            config: Masking configuration

        Returns:
            DataFrame with masked column
        """
        if config is None:
            config = MaskingConfig(
                strategy=MaskingStrategy[strategy.upper()]
            )

        df[column] = df[column].apply(
            lambda x: self.mask(str(x), config=config) if x is not None else x
        )

        return df

    def get_token_mapping(self) -> Dict[str, str]:
        """
        Get token mapping for detokenization.

        Returns:
            Dictionary mapping original values to tokens
        """
        return self._token_map.copy()

    def clear_tokens(self):
        """Clear token mapping."""
        self._token_map.clear()


class MaskingPresets:
    """Preset masking configurations."""

    @staticmethod
    def credit_card() -> MaskingConfig:
        """Masking config for credit cards (show last 4)."""
        return MaskingConfig(
            strategy=MaskingStrategy.PARTIAL,
            partial_reveal_end=4,
            mask_char="*"
        )

    @staticmethod
    def ssn() -> MaskingConfig:
        """Masking config for SSN (show last 4)."""
        return MaskingConfig(
            strategy=MaskingStrategy.PARTIAL,
            partial_reveal_end=4,
            mask_char="*"
        )

    @staticmethod
    def email_hash() -> MaskingConfig:
        """Masking config for email (hash)."""
        return MaskingConfig(
            strategy=MaskingStrategy.HASH,
            hash_algorithm="sha256"
        )

    @staticmethod
    def phone_partial() -> MaskingConfig:
        """Masking config for phone (show last 4)."""
        return MaskingConfig(
            strategy=MaskingStrategy.PARTIAL,
            partial_reveal_end=4,
            mask_char="*"
        )

    @staticmethod
    def full_redact() -> MaskingConfig:
        """Full redaction."""
        return MaskingConfig(
            strategy=MaskingStrategy.REDACT,
            preserve_length=True,
            mask_char="*"
        )

    @staticmethod
    def tokenize() -> MaskingConfig:
        """Tokenization."""
        return MaskingConfig(
            strategy=MaskingStrategy.TOKENIZE
        )


__all__ = [
    "DataMasker",
    "MaskingStrategy",
    "MaskingConfig",
    "MaskingPresets"
]
