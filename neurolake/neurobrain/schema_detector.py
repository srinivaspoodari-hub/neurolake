"""
NeuroLake Schema Detector
AI-powered automatic schema detection and inference
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime
import json


class DataType(Enum):
    """Detected data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"
    JSON = "json"
    ARRAY = "array"
    BINARY = "binary"
    UNKNOWN = "unknown"


class PIIType(Enum):
    """PII classification"""
    NONE = "none"
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    NAME = "name"
    DOB = "date_of_birth"
    PASSPORT = "passport"
    LICENSE = "drivers_license"


@dataclass
class ColumnSchema:
    """Detected column schema"""
    name: str
    data_type: DataType
    nullable: bool
    unique: bool
    primary_key_candidate: bool
    pii_type: PIIType
    sample_values: List[Any]
    null_count: int
    unique_count: int
    total_count: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    avg_length: Optional[float] = None
    pattern: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedSchema:
    """Complete detected schema"""
    columns: List[ColumnSchema]
    row_count: int
    estimated_size_bytes: int
    encoding: str
    has_header: bool
    delimiter: Optional[str] = None
    primary_key_candidates: List[str] = field(default_factory=list)
    foreign_key_candidates: List[Dict] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaDetector:
    """AI-powered schema detection engine"""

    # Regex patterns for specialized types
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$',
        'url': r'^https?://[^\s]+$',
        'ip_address': r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
        'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
        'credit_card': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',
        'date_iso': r'^\d{4}-\d{2}-\d{2}$',
        'datetime_iso': r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
    }

    def __init__(self, sample_size: int = 10000):
        """
        Initialize schema detector

        Args:
            sample_size: Number of rows to sample for detection
        """
        self.sample_size = sample_size

    def detect_from_file(self, file_path: str, **kwargs) -> DetectedSchema:
        """
        Detect schema from file

        Args:
            file_path: Path to file
            **kwargs: Additional parameters for file reading

        Returns:
            DetectedSchema with complete analysis
        """
        # Detect file type and encoding
        encoding = self._detect_encoding(file_path)
        file_type = self._detect_file_type(file_path)

        # Read file based on type
        if file_type == 'csv':
            delimiter = self._detect_delimiter(file_path, encoding)
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter,
                           nrows=self.sample_size, **kwargs)
            has_header = True
        elif file_type == 'json':
            df = pd.read_json(file_path, lines=True, nrows=self.sample_size)
            delimiter = None
            has_header = True
        elif file_type == 'parquet':
            df = pd.read_parquet(file_path)
            delimiter = None
            has_header = True
        elif file_type == 'excel':
            df = pd.read_excel(file_path, nrows=self.sample_size)
            delimiter = None
            has_header = True
        else:
            # Try CSV as default
            df = pd.read_csv(file_path, encoding=encoding, nrows=self.sample_size)
            delimiter = ','
            has_header = True

        return self.detect_from_dataframe(df, encoding=encoding,
                                         delimiter=delimiter, has_header=has_header)

    def detect_from_dataframe(self, df: pd.DataFrame, encoding: str = 'utf-8',
                              delimiter: Optional[str] = None,
                              has_header: bool = True) -> DetectedSchema:
        """
        Detect schema from pandas DataFrame

        Args:
            df: pandas DataFrame
            encoding: File encoding
            delimiter: CSV delimiter if applicable
            has_header: Whether data has header row

        Returns:
            DetectedSchema with complete analysis
        """
        columns = []

        for col_name in df.columns:
            column_schema = self._analyze_column(col_name, df[col_name])
            columns.append(column_schema)

        # Detect primary key candidates
        pk_candidates = self._detect_primary_keys(columns)

        # Detect foreign key candidates
        fk_candidates = self._detect_foreign_keys(columns)

        # Estimate size
        estimated_size = df.memory_usage(deep=True).sum()

        schema = DetectedSchema(
            columns=columns,
            row_count=len(df),
            estimated_size_bytes=int(estimated_size),
            encoding=encoding,
            has_header=has_header,
            delimiter=delimiter,
            primary_key_candidates=pk_candidates,
            foreign_key_candidates=fk_candidates,
            confidence=self._calculate_overall_confidence(columns)
        )

        return schema

    def _analyze_column(self, col_name: str, series: pd.Series) -> ColumnSchema:
        """Analyze a single column"""
        # Basic statistics
        null_count = int(series.isnull().sum())
        total_count = len(series)
        non_null_series = series.dropna()
        unique_count = int(series.nunique())

        # Detect data type
        data_type, confidence = self._detect_data_type(non_null_series)

        # Detect PII
        pii_type = self._detect_pii(col_name, non_null_series, data_type)

        # Sample values
        sample_values = non_null_series.head(5).tolist()

        # Min/max values
        min_value, max_value = self._get_min_max(non_null_series, data_type)

        # Average length for strings
        avg_length = None
        if data_type == DataType.STRING:
            avg_length = float(non_null_series.astype(str).str.len().mean())

        # Detect pattern for strings
        pattern = None
        if data_type == DataType.STRING:
            pattern = self._detect_pattern(non_null_series)

        # Determine if nullable, unique, primary key candidate
        nullable = null_count > 0
        unique = unique_count == total_count
        primary_key_candidate = unique and null_count == 0 and unique_count > 0

        return ColumnSchema(
            name=col_name,
            data_type=data_type,
            nullable=nullable,
            unique=unique,
            primary_key_candidate=primary_key_candidate,
            pii_type=pii_type,
            sample_values=sample_values,
            null_count=null_count,
            unique_count=unique_count,
            total_count=total_count,
            min_value=min_value,
            max_value=max_value,
            avg_length=avg_length,
            pattern=pattern,
            confidence=confidence
        )

    def _detect_data_type(self, series: pd.Series) -> tuple[DataType, float]:
        """Detect data type with confidence score"""
        if len(series) == 0:
            return DataType.UNKNOWN, 0.0

        # Try specialized patterns first
        sample = series.head(100).astype(str)

        # Email detection
        if self._matches_pattern(sample, self.PATTERNS['email'], threshold=0.8):
            return DataType.EMAIL, 0.95

        # Phone detection
        if self._matches_pattern(sample, self.PATTERNS['phone'], threshold=0.8):
            return DataType.PHONE, 0.95

        # URL detection
        if self._matches_pattern(sample, self.PATTERNS['url'], threshold=0.8):
            return DataType.URL, 0.95

        # IP address detection
        if self._matches_pattern(sample, self.PATTERNS['ip_address'], threshold=0.9):
            return DataType.IP_ADDRESS, 0.95

        # Try to infer from pandas dtype
        dtype = series.dtype

        if pd.api.types.is_integer_dtype(dtype):
            return DataType.INTEGER, 1.0
        elif pd.api.types.is_float_dtype(dtype):
            return DataType.FLOAT, 1.0
        elif pd.api.types.is_bool_dtype(dtype):
            return DataType.BOOLEAN, 1.0
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return DataType.DATETIME, 1.0

        # Try to parse as different types
        # Try boolean
        unique_values = set(series.astype(str).str.lower().unique())
        if unique_values.issubset({'true', 'false', 't', 'f', '1', '0', 'yes', 'no', 'y', 'n'}):
            return DataType.BOOLEAN, 0.9

        # Try integer
        try:
            pd.to_numeric(series, errors='raise')
            if (series == series.astype(int)).all():
                return DataType.INTEGER, 0.95
            else:
                return DataType.FLOAT, 0.95
        except (ValueError, TypeError):
            pass

        # Try datetime
        try:
            pd.to_datetime(series, errors='raise')
            return DataType.DATETIME, 0.9
        except (ValueError, TypeError):
            pass

        # Try JSON
        try:
            sample_val = series.iloc[0]
            if isinstance(sample_val, str) and (sample_val.startswith('{') or sample_val.startswith('[')):
                json.loads(sample_val)
                return DataType.JSON, 0.85
        except (json.JSONDecodeError, IndexError):
            pass

        # Default to string
        return DataType.STRING, 0.8

    def _detect_pii(self, col_name: str, series: pd.Series, data_type: DataType) -> PIIType:
        """Detect PII type"""
        col_name_lower = col_name.lower()

        # Email
        if data_type == DataType.EMAIL or 'email' in col_name_lower:
            return PIIType.EMAIL

        # Phone
        if data_type == DataType.PHONE or 'phone' in col_name_lower or 'tel' in col_name_lower:
            return PIIType.PHONE

        # SSN
        if 'ssn' in col_name_lower or 'social_security' in col_name_lower:
            sample = series.head(100).astype(str)
            if self._matches_pattern(sample, self.PATTERNS['ssn'], threshold=0.8):
                return PIIType.SSN

        # Credit card
        if 'card' in col_name_lower or 'credit' in col_name_lower:
            sample = series.head(100).astype(str)
            if self._matches_pattern(sample, self.PATTERNS['credit_card'], threshold=0.8):
                return PIIType.CREDIT_CARD

        # Name
        if any(keyword in col_name_lower for keyword in ['name', 'first_name', 'last_name', 'full_name']):
            return PIIType.NAME

        # Address
        if any(keyword in col_name_lower for keyword in ['address', 'street', 'city', 'zip', 'postal']):
            return PIIType.ADDRESS

        # DOB
        if any(keyword in col_name_lower for keyword in ['dob', 'birth', 'birthdate']):
            return PIIType.DOB

        return PIIType.NONE

    def _matches_pattern(self, series: pd.Series, pattern: str, threshold: float = 0.8) -> bool:
        """Check if series values match a regex pattern"""
        if len(series) == 0:
            return False

        matches = series.str.match(pattern, na=False)
        match_ratio = matches.sum() / len(series)
        return match_ratio >= threshold

    def _get_min_max(self, series: pd.Series, data_type: DataType) -> tuple:
        """Get min and max values"""
        try:
            if data_type in [DataType.INTEGER, DataType.FLOAT, DataType.DECIMAL]:
                return float(series.min()), float(series.max())
            elif data_type in [DataType.DATE, DataType.DATETIME, DataType.TIMESTAMP]:
                return str(series.min()), str(series.max())
            elif data_type == DataType.STRING:
                min_len = series.astype(str).str.len().min()
                max_len = series.astype(str).str.len().max()
                return int(min_len), int(max_len)
        except Exception:
            pass
        return None, None

    def _detect_pattern(self, series: pd.Series) -> Optional[str]:
        """Detect common pattern in string data"""
        if len(series) == 0:
            return None

        # Check known patterns
        sample = series.head(100).astype(str)
        for pattern_name, pattern in self.PATTERNS.items():
            if self._matches_pattern(sample, pattern, threshold=0.7):
                return pattern_name

        return None

    def _detect_primary_keys(self, columns: List[ColumnSchema]) -> List[str]:
        """Detect primary key candidates"""
        candidates = []
        for col in columns:
            if col.primary_key_candidate:
                candidates.append(col.name)
        return candidates

    def _detect_foreign_keys(self, columns: List[ColumnSchema]) -> List[Dict]:
        """Detect foreign key candidates"""
        # Simple heuristic: columns ending with _id that are not unique
        fk_candidates = []
        for col in columns:
            if col.name.lower().endswith('_id') and not col.unique:
                fk_candidates.append({
                    'column': col.name,
                    'referenced_table': col.name[:-3],  # Remove '_id'
                    'confidence': 0.7
                })
        return fk_candidates

    def _calculate_overall_confidence(self, columns: List[ColumnSchema]) -> float:
        """Calculate overall schema detection confidence"""
        if not columns:
            return 0.0
        avg_confidence = sum(col.confidence for col in columns) / len(columns)
        return round(avg_confidence, 2)

    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        import chardet

        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except Exception:
            return 'utf-8'

    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension"""
        if file_path.endswith('.csv'):
            return 'csv'
        elif file_path.endswith('.json') or file_path.endswith('.jsonl'):
            return 'json'
        elif file_path.endswith('.parquet'):
            return 'parquet'
        elif file_path.endswith(('.xls', '.xlsx')):
            return 'excel'
        else:
            return 'csv'  # Default

    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        """Detect CSV delimiter"""
        import csv

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except Exception:
            return ','  # Default to comma

    def export_schema_to_dict(self, schema: DetectedSchema) -> Dict:
        """Export schema to dictionary"""
        return {
            'columns': [
                {
                    'name': col.name,
                    'data_type': col.data_type.value,
                    'nullable': col.nullable,
                    'unique': col.unique,
                    'primary_key_candidate': col.primary_key_candidate,
                    'pii_type': col.pii_type.value,
                    'sample_values': col.sample_values,
                    'null_count': col.null_count,
                    'unique_count': col.unique_count,
                    'total_count': col.total_count,
                    'min_value': col.min_value,
                    'max_value': col.max_value,
                    'avg_length': col.avg_length,
                    'pattern': col.pattern,
                    'confidence': col.confidence
                }
                for col in schema.columns
            ],
            'row_count': schema.row_count,
            'estimated_size_bytes': schema.estimated_size_bytes,
            'encoding': schema.encoding,
            'has_header': schema.has_header,
            'delimiter': schema.delimiter,
            'primary_key_candidates': schema.primary_key_candidates,
            'foreign_key_candidates': schema.foreign_key_candidates,
            'confidence': schema.confidence
        }
