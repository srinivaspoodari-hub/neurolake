"""
NeuroLake Metadata Normalization Layer
Handles metadata from multiple ETL sources with canonical data model (CDM)
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json


class DataType(Enum):
    """Canonical data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BINARY = "binary"
    ARRAY = "array"
    STRUCT = "struct"
    MAP = "map"


class SourcePlatform(Enum):
    """Supported source platforms"""
    TALEND = "talend"
    INFORMATICA = "informatica"
    DATASTAGE = "datastage"
    SSIS = "ssis"
    PENTAHO = "pentaho"
    ABINITIO = "abinitio"
    SQL_SERVER = "sql_server"
    ORACLE = "oracle"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    TERADATA = "teradata"


@dataclass
class CanonicalColumn:
    """Canonical column representation"""
    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalTable:
    """Canonical table representation"""
    name: str
    schema: str
    columns: List[CanonicalColumn]
    source_platform: SourcePlatform
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TypeMappingRegistry:
    """Registry for type mappings across platforms"""

    TYPE_MAPPINGS = {
        # SQL Server to Canonical
        SourcePlatform.SQL_SERVER: {
            'varchar': DataType.STRING,
            'nvarchar': DataType.STRING,
            'char': DataType.STRING,
            'text': DataType.STRING,
            'int': DataType.INTEGER,
            'bigint': DataType.INTEGER,
            'smallint': DataType.INTEGER,
            'tinyint': DataType.INTEGER,
            'decimal': DataType.DECIMAL,
            'numeric': DataType.DECIMAL,
            'float': DataType.FLOAT,
            'real': DataType.FLOAT,
            'bit': DataType.BOOLEAN,
            'date': DataType.DATE,
            'datetime': DataType.TIMESTAMP,
            'datetime2': DataType.TIMESTAMP,
            'varbinary': DataType.BINARY,
        },

        # Oracle to Canonical
        SourcePlatform.ORACLE: {
            'VARCHAR2': DataType.STRING,
            'NVARCHAR2': DataType.STRING,
            'CHAR': DataType.STRING,
            'CLOB': DataType.STRING,
            'NUMBER': DataType.DECIMAL,
            'BINARY_FLOAT': DataType.FLOAT,
            'BINARY_DOUBLE': DataType.FLOAT,
            'DATE': DataType.TIMESTAMP,  # Oracle DATE includes time
            'TIMESTAMP': DataType.TIMESTAMP,
            'BLOB': DataType.BINARY,
            'RAW': DataType.BINARY,
        },

        # PostgreSQL to Canonical
        SourcePlatform.POSTGRES: {
            'varchar': DataType.STRING,
            'text': DataType.STRING,
            'char': DataType.STRING,
            'integer': DataType.INTEGER,
            'bigint': DataType.INTEGER,
            'smallint': DataType.INTEGER,
            'numeric': DataType.DECIMAL,
            'decimal': DataType.DECIMAL,
            'real': DataType.FLOAT,
            'double precision': DataType.FLOAT,
            'boolean': DataType.BOOLEAN,
            'date': DataType.DATE,
            'timestamp': DataType.TIMESTAMP,
            'bytea': DataType.BINARY,
            'array': DataType.ARRAY,
            'json': DataType.STRING,
            'jsonb': DataType.STRING,
        },

        # Teradata to Canonical
        SourcePlatform.TERADATA: {
            'VARCHAR': DataType.STRING,
            'CHAR': DataType.STRING,
            'INTEGER': DataType.INTEGER,
            'BIGINT': DataType.INTEGER,
            'SMALLINT': DataType.INTEGER,
            'DECIMAL': DataType.DECIMAL,
            'NUMERIC': DataType.DECIMAL,
            'FLOAT': DataType.FLOAT,
            'DATE': DataType.DATE,
            'TIMESTAMP': DataType.TIMESTAMP,
            'BYTE': DataType.BINARY,
            'VARBYTE': DataType.BINARY,
        },
    }

    @classmethod
    def map_type(cls, source_type: str, source_platform: SourcePlatform) -> DataType:
        """Map source type to canonical type"""
        mappings = cls.TYPE_MAPPINGS.get(source_platform, {})
        canonical_type = mappings.get(source_type.upper(), DataType.STRING)
        return canonical_type


class MetadataNormalizer:
    """Normalizes metadata from different sources to canonical model"""

    def __init__(self):
        self.type_registry = TypeMappingRegistry()
        self.normalization_history: List[Dict] = []

    def normalize_talend_metadata(self, talend_schema: Dict) -> CanonicalTable:
        """Normalize Talend schema to canonical format"""
        columns = []

        for col in talend_schema.get('columns', []):
            canonical_col = CanonicalColumn(
                name=col['name'],
                data_type=self._map_talend_type(col['type']),
                nullable=col.get('nullable', True),
                description=col.get('comment'),
                metadata={'talend_type': col['type'], 'length': col.get('length')}
            )
            columns.append(canonical_col)

        table = CanonicalTable(
            name=talend_schema['table_name'],
            schema=talend_schema.get('schema', 'default'),
            columns=columns,
            source_platform=SourcePlatform.TALEND,
            description=talend_schema.get('description'),
            metadata={'original_schema': talend_schema}
        )

        self._log_normalization(SourcePlatform.TALEND, table)
        return table

    def normalize_informatica_metadata(self, informatica_source: Dict) -> CanonicalTable:
        """Normalize Informatica source to canonical format"""
        columns = []

        for port in informatica_source.get('source_ports', []):
            canonical_col = CanonicalColumn(
                name=port['port_name'],
                data_type=self._map_informatica_type(port['datatype']),
                nullable=not port.get('not_null', False),
                primary_key=port.get('key_type') == 'PRIMARY KEY',
                description=port.get('description'),
                metadata={
                    'informatica_type': port['datatype'],
                    'precision': port.get('precision'),
                    'scale': port.get('scale')
                }
            )
            columns.append(canonical_col)

        table = CanonicalTable(
            name=informatica_source['source_name'],
            schema=informatica_source.get('database_name', 'default'),
            columns=columns,
            source_platform=SourcePlatform.INFORMATICA,
            description=informatica_source.get('description'),
            metadata={'original_source': informatica_source}
        )

        self._log_normalization(SourcePlatform.INFORMATICA, table)
        return table

    def normalize_sql_metadata(self, sql_table: Dict, platform: SourcePlatform) -> CanonicalTable:
        """Normalize SQL metadata to canonical format"""
        columns = []

        for col in sql_table.get('columns', []):
            canonical_col = CanonicalColumn(
                name=col['column_name'],
                data_type=self.type_registry.map_type(col['data_type'], platform),
                nullable=col.get('is_nullable', 'YES') == 'YES',
                primary_key=col.get('column_key') == 'PRI',
                default_value=col.get('column_default'),
                description=col.get('column_comment'),
                metadata={
                    'original_type': col['data_type'],
                    'character_maximum_length': col.get('character_maximum_length'),
                    'numeric_precision': col.get('numeric_precision'),
                    'numeric_scale': col.get('numeric_scale')
                }
            )
            columns.append(canonical_col)

        table = CanonicalTable(
            name=sql_table['table_name'],
            schema=sql_table.get('table_schema', 'default'),
            columns=columns,
            source_platform=platform,
            description=sql_table.get('table_comment'),
            metadata={'original_table': sql_table}
        )

        self._log_normalization(platform, table)
        return table

    def _map_talend_type(self, talend_type: str) -> DataType:
        """Map Talend data type to canonical type"""
        type_map = {
            'id_String': DataType.STRING,
            'id_Integer': DataType.INTEGER,
            'id_Long': DataType.INTEGER,
            'id_BigDecimal': DataType.DECIMAL,
            'id_Double': DataType.FLOAT,
            'id_Float': DataType.FLOAT,
            'id_Boolean': DataType.BOOLEAN,
            'id_Date': DataType.TIMESTAMP,
            'id_byte': DataType.BINARY,
        }
        return type_map.get(talend_type, DataType.STRING)

    def _map_informatica_type(self, informatica_type: str) -> DataType:
        """Map Informatica data type to canonical type"""
        type_map = {
            'string': DataType.STRING,
            'integer': DataType.INTEGER,
            'bigint': DataType.INTEGER,
            'decimal': DataType.DECIMAL,
            'double': DataType.FLOAT,
            'date/time': DataType.TIMESTAMP,
            'date': DataType.DATE,
            'binary': DataType.BINARY,
            'nstring': DataType.STRING,
        }
        return type_map.get(informatica_type.lower(), DataType.STRING)

    def _log_normalization(self, platform: SourcePlatform, table: CanonicalTable):
        """Log normalization for audit trail"""
        self.normalization_history.append({
            'timestamp': datetime.now().isoformat(),
            'platform': platform.value,
            'table': table.name,
            'schema': table.schema,
            'column_count': len(table.columns)
        })

    def detect_schema_drift(self, old_table: CanonicalTable, new_table: CanonicalTable) -> Dict:
        """Detect schema drift between old and new versions"""
        drift = {
            'columns_added': [],
            'columns_removed': [],
            'columns_modified': [],
            'type_changes': []
        }

        old_cols = {c.name: c for c in old_table.columns}
        new_cols = {c.name: c for c in new_table.columns}

        # Detect added columns
        for col_name in new_cols:
            if col_name not in old_cols:
                drift['columns_added'].append(col_name)

        # Detect removed columns
        for col_name in old_cols:
            if col_name not in new_cols:
                drift['columns_removed'].append(col_name)

        # Detect modified columns
        for col_name in old_cols:
            if col_name in new_cols:
                old_col = old_cols[col_name]
                new_col = new_cols[col_name]

                if old_col.data_type != new_col.data_type:
                    drift['type_changes'].append({
                        'column': col_name,
                        'old_type': old_col.data_type.value,
                        'new_type': new_col.data_type.value
                    })

                if old_col.nullable != new_col.nullable:
                    drift['columns_modified'].append({
                        'column': col_name,
                        'change': 'nullable',
                        'old_value': old_col.nullable,
                        'new_value': new_col.nullable
                    })

        return drift

    def export_to_spark_schema(self, table: CanonicalTable) -> str:
        """Export canonical table to Spark schema DDL"""
        type_map = {
            DataType.STRING: 'STRING',
            DataType.INTEGER: 'LONG',
            DataType.FLOAT: 'DOUBLE',
            DataType.DECIMAL: 'DECIMAL(38,10)',
            DataType.BOOLEAN: 'BOOLEAN',
            DataType.DATE: 'DATE',
            DataType.TIMESTAMP: 'TIMESTAMP',
            DataType.BINARY: 'BINARY',
            DataType.ARRAY: 'ARRAY<STRING>',
            DataType.STRUCT: 'STRUCT<>',
            DataType.MAP: 'MAP<STRING,STRING>'
        }

        columns_ddl = []
        for col in table.columns:
            spark_type = type_map.get(col.data_type, 'STRING')
            nullable = '' if col.nullable else ' NOT NULL'
            comment = f" COMMENT '{col.description}'" if col.description else ''
            columns_ddl.append(f"    {col.name} {spark_type}{nullable}{comment}")

        ddl = f"""CREATE TABLE {table.schema}.{table.name} (
{',\n'.join(columns_ddl)}
)"""
        return ddl

    def get_normalization_stats(self) -> Dict:
        """Get normalization statistics"""
        stats = {
            'total_normalizations': len(self.normalization_history),
            'platforms': {},
            'recent_normalizations': self.normalization_history[-10:]
        }

        for entry in self.normalization_history:
            platform = entry['platform']
            stats['platforms'][platform] = stats['platforms'].get(platform, 0) + 1

        return stats
