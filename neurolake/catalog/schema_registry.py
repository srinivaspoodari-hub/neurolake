"""
Schema Registry - Centralized schema management and evolution tracking
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Centralized schema registry for NeuroLake

    Manages:
    - Schema definitions and versions
    - Schema evolution and compatibility
    - Column metadata and data types
    - Schema validation
    """

    def __init__(self, storage_path: str = "./schema_registry"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.schemas: Dict[str, List[Dict]] = {}  # schema_name -> list of versions
        self._load_schemas()

    def _load_schemas(self):
        """Load schemas from storage"""
        schema_file = self.storage_path / "schemas.json"
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    self.schemas = json.load(f)
                logger.info(f"Loaded {len(self.schemas)} schemas")
            except Exception as e:
                logger.error(f"Error loading schemas: {e}")

    def _save_schemas(self):
        """Save schemas to storage"""
        schema_file = self.storage_path / "schemas.json"
        try:
            with open(schema_file, 'w') as f:
                json.dump(self.schemas, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving schemas: {e}")

    def register_schema(
        self,
        schema_name: str,
        columns: List[Dict],
        description: str = "",
        metadata: Dict = None
    ) -> int:
        """
        Register a new schema or new version of existing schema

        Args:
            schema_name: Unique schema name
            columns: List of column definitions
            description: Schema description
            metadata: Additional metadata

        Returns:
            Version number
        """
        if schema_name not in self.schemas:
            self.schemas[schema_name] = []

        version = len(self.schemas[schema_name]) + 1

        schema_record = {
            'schema_name': schema_name,
            'version': version,
            'columns': columns,
            'description': description,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'compatible_with': self._check_compatibility(schema_name, columns)
        }

        self.schemas[schema_name].append(schema_record)
        self._save_schemas()

        logger.info(f"Registered schema {schema_name} v{version}")
        return version

    def _check_compatibility(self, schema_name: str, new_columns: List[Dict]) -> List[int]:
        """Check which previous versions are compatible with new schema"""
        compatible_versions = []

        if schema_name not in self.schemas:
            return compatible_versions

        for existing_schema in self.schemas[schema_name]:
            existing_cols = {col['name']: col for col in existing_schema['columns']}
            new_cols = {col['name']: col for col in new_columns}

            # Check backward compatibility
            # New schema is compatible if all existing columns are present with same types
            is_compatible = True
            for col_name, col_def in existing_cols.items():
                if col_name not in new_cols:
                    is_compatible = False
                    break
                if new_cols[col_name].get('type') != col_def.get('type'):
                    is_compatible = False
                    break

            if is_compatible:
                compatible_versions.append(existing_schema['version'])

        return compatible_versions

    def get_schema(self, schema_name: str, version: Optional[int] = None) -> Optional[Dict]:
        """Get schema by name and version (latest if version not specified)"""
        if schema_name not in self.schemas:
            return None

        schema_versions = self.schemas[schema_name]
        if not schema_versions:
            return None

        if version is None:
            return schema_versions[-1]  # Latest version

        for schema in schema_versions:
            if schema['version'] == version:
                return schema

        return None

    def get_schema_evolution(self, schema_name: str) -> List[Dict]:
        """Get all versions of a schema showing evolution"""
        return self.schemas.get(schema_name, [])

    def validate_data(self, schema_name: str, data: Dict, version: Optional[int] = None) -> Dict:
        """
        Validate data against schema

        Returns:
            {"valid": bool, "errors": []}
        """
        schema = self.get_schema(schema_name, version)
        if not schema:
            return {"valid": False, "errors": [f"Schema {schema_name} not found"]}

        errors = []
        schema_cols = {col['name']: col for col in schema['columns']}

        # Check all required columns are present
        for col_name, col_def in schema_cols.items():
            if not col_def.get('nullable', True) and col_name not in data:
                errors.append(f"Required column '{col_name}' is missing")

        # Check data types (simplified validation)
        for col_name, value in data.items():
            if col_name not in schema_cols:
                errors.append(f"Unknown column '{col_name}'")
                continue

            expected_type = schema_cols[col_name].get('type', 'string')
            # Type checking can be expanded based on needs

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
