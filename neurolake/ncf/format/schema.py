"""
NCF Schema Definition

Defines the schema for NCF files including:
- Column names and types
- Semantic metadata
- Statistics
- Compression settings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import msgpack


class NCFDataType(Enum):
    """Supported data types in NCF"""
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"
    BINARY = "binary"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    DECIMAL = "decimal"


class SemanticType(Enum):
    """Semantic types for AI understanding"""
    UNKNOWN = "unknown"
    PII_EMAIL = "pii_email"
    PII_PHONE = "pii_phone"
    PII_SSN = "pii_ssn"
    PII_NAME = "pii_name"
    PII_ADDRESS = "pii_address"
    GEOGRAPHIC_LAT = "geo_lat"
    GEOGRAPHIC_LON = "geo_lon"
    TEMPORAL_DATE = "temporal_date"
    TEMPORAL_TIMESTAMP = "temporal_timestamp"
    IDENTIFIER_UUID = "id_uuid"
    IDENTIFIER_KEY = "id_key"
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    TEXT_DESCRIPTION = "text_description"
    TEXT_TITLE = "text_title"


@dataclass
class ColumnStatistics:
    """Statistics for a single column"""
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    null_count: int = 0
    distinct_count: Optional[int] = None
    total_count: int = 0
    avg_length: Optional[float] = None  # For string/binary columns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_value": str(self.min_value) if self.min_value is not None else None,
            "max_value": str(self.max_value) if self.max_value is not None else None,
            "null_count": self.null_count,
            "distinct_count": self.distinct_count,
            "total_count": self.total_count,
            "avg_length": self.avg_length,
        }


@dataclass
class ColumnSchema:
    """Schema definition for a single column"""
    name: str
    data_type: NCFDataType
    nullable: bool = True
    semantic_type: SemanticType = SemanticType.UNKNOWN
    description: Optional[str] = None
    statistics: Optional[ColumnStatistics] = None

    # Compression settings
    compression_model: Optional[str] = None
    use_dictionary: bool = False

    # Index settings
    create_learned_index: bool = False
    index_model_type: Optional[str] = None

    # Metadata for AI agents
    contains_pii: bool = False
    typical_query_patterns: List[str] = field(default_factory=list)
    column_group: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type.value,
            "nullable": self.nullable,
            "semantic_type": self.semantic_type.value,
            "description": self.description,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "compression_model": self.compression_model,
            "use_dictionary": self.use_dictionary,
            "create_learned_index": self.create_learned_index,
            "index_model_type": self.index_model_type,
            "contains_pii": self.contains_pii,
            "typical_query_patterns": self.typical_query_patterns,
            "column_group": self.column_group,
        }


@dataclass
class NCFSchema:
    """
    Complete schema for an NCF file

    Defines table structure, column types, semantics, and metadata.
    """
    table_name: str
    columns: List[ColumnSchema]
    version: int = 1
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    row_count: int = 0

    # Global settings
    default_compression: str = "zstd"
    enable_learned_indexes: bool = True

    # Column grouping (columns accessed together)
    column_groups: Dict[int, List[str]] = field(default_factory=dict)

    def get_column(self, name: str) -> Optional[ColumnSchema]:
        """Get column schema by name"""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def column_names(self) -> List[str]:
        """Get list of all column names"""
        return [col.name for col in self.columns]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize schema to dictionary"""
        return {
            "table_name": self.table_name,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "row_count": self.row_count,
            "default_compression": self.default_compression,
            "enable_learned_indexes": self.enable_learned_indexes,
            "columns": [col.to_dict() for col in self.columns],
            "column_groups": {
                group_id: cols for group_id, cols in self.column_groups.items()
            },
        }

    def to_json(self) -> str:
        """Serialize schema to JSON"""
        return json.dumps(self.to_dict(), indent=2)

    def to_msgpack(self) -> bytes:
        """Serialize schema to msgpack format"""
        return msgpack.packb(self.to_dict())

    @classmethod
    def from_msgpack(cls, data: bytes) -> "NCFSchema":
        """Deserialize schema from msgpack format"""
        return cls.from_dict(msgpack.unpackb(data, raw=False))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NCFSchema":
        """Deserialize schema from dictionary"""
        columns = [
            ColumnSchema(
                name=col["name"],
                data_type=NCFDataType(col["data_type"]),
                nullable=col.get("nullable", True),
                semantic_type=SemanticType(col.get("semantic_type", "unknown")),
                description=col.get("description"),
                compression_model=col.get("compression_model"),
                use_dictionary=col.get("use_dictionary", False),
                create_learned_index=col.get("create_learned_index", False),
                index_model_type=col.get("index_model_type"),
                contains_pii=col.get("contains_pii", False),
                typical_query_patterns=col.get("typical_query_patterns", []),
                column_group=col.get("column_group"),
            )
            for col in data["columns"]
        ]

        return cls(
            table_name=data["table_name"],
            columns=columns,
            version=data.get("version", 1),
            created_at=data.get("created_at"),
            modified_at=data.get("modified_at"),
            row_count=data.get("row_count", 0),
            default_compression=data.get("default_compression", "zstd"),
            enable_learned_indexes=data.get("enable_learned_indexes", True),
            column_groups=data.get("column_groups", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "NCFSchema":
        """Deserialize schema from JSON"""
        return cls.from_dict(json.loads(json_str))


# Example usage
if __name__ == "__main__":
    # Create a sample schema
    schema = NCFSchema(
        table_name="users",
        columns=[
            ColumnSchema(
                name="id",
                data_type=NCFDataType.INT64,
                nullable=False,
                semantic_type=SemanticType.IDENTIFIER_KEY,
                create_learned_index=True,
            ),
            ColumnSchema(
                name="email",
                data_type=NCFDataType.STRING,
                semantic_type=SemanticType.PII_EMAIL,
                contains_pii=True,
                use_dictionary=True,
                column_group=1,
            ),
            ColumnSchema(
                name="name",
                data_type=NCFDataType.STRING,
                semantic_type=SemanticType.PII_NAME,
                contains_pii=True,
                column_group=1,
            ),
            ColumnSchema(
                name="created_at",
                data_type=NCFDataType.TIMESTAMP,
                semantic_type=SemanticType.TEMPORAL_TIMESTAMP,
                create_learned_index=True,
            ),
        ],
        column_groups={
            1: ["email", "name"],  # Accessed together
        },
    )

    # Serialize
    print("Schema JSON:")
    print(schema.to_json())

    # Deserialize
    schema2 = NCFSchema.from_json(schema.to_json())
    print(f"\nTable: {schema2.table_name}")
    print(f"Columns: {schema2.column_names()}")
