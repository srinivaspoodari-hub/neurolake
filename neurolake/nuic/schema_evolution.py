"""
Schema Evolution Tracker

Tracks schema changes over time with versioning, comparison, and impact analysis.
Detects breaking changes, backward compatibility, and provides schema migration suggestions.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of schema changes"""
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_RENAMED = "column_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    PII_CHANGED = "pii_changed"
    POSITION_CHANGED = "position_changed"
    METADATA_CHANGED = "metadata_changed"


class SeverityLevel(Enum):
    """Severity of schema changes"""
    BREAKING = "breaking"  # Cannot read old data
    MAJOR = "major"  # May break consumers
    MINOR = "minor"  # Backward compatible
    PATCH = "patch"  # Metadata only


@dataclass
class SchemaChange:
    """Represents a single schema change"""
    change_type: ChangeType
    severity: SeverityLevel
    column_name: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    description: str
    impact: str


@dataclass
class SchemaVersion:
    """Schema version with full definition"""
    version_id: str
    dataset_id: str
    version_number: int
    columns: List[Dict[str, Any]]
    changed_at: str
    changed_by: str
    change_description: str


class SchemaEvolutionTracker:
    """
    Tracks and manages schema evolution over time

    Capabilities:
    - Version comparison
    - Breaking change detection
    - Backward compatibility analysis
    - Migration suggestion generation
    - Impact analysis
    """

    def __init__(self, catalog_engine):
        """
        Initialize Schema Evolution Tracker

        Args:
            catalog_engine: NUICEngine instance
        """
        self.catalog = catalog_engine
        self.conn = catalog_engine.conn

    def evolve_schema(
        self,
        dataset_id: str,
        new_columns: List[Dict[str, Any]],
        changed_by: str = "system",
        change_description: Optional[str] = None
    ) -> Tuple[int, List[SchemaChange]]:
        """
        Evolve dataset schema to new version

        Args:
            dataset_id: Dataset identifier
            new_columns: New column definitions
            changed_by: User making the change
            change_description: Description of changes

        Returns:
            Tuple of (new_version_number, list of changes)
        """
        # Get current schema
        dataset = self.catalog.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        current_version = dataset['schema_version']
        current_columns = dataset['columns']

        # Detect changes
        changes = self.compare_schemas(current_columns, new_columns)

        if not changes:
            logger.info(f"No schema changes detected for {dataset_id}")
            return current_version, []

        # Determine new version number
        new_version = current_version + 1

        # Check for breaking changes
        breaking_changes = [c for c in changes if c.severity == SeverityLevel.BREAKING]
        if breaking_changes:
            logger.warning(f"Detected {len(breaking_changes)} breaking changes in {dataset_id}")

        # Save new schema version
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        version_id = f"{dataset_id}_v{new_version}"

        # Auto-generate change description if not provided
        if not change_description:
            change_description = self._generate_change_description(changes)

        try:
            # Insert schema version
            cursor.execute("""
                INSERT INTO schema_versions (
                    version_id, dataset_id, schema_version, columns,
                    changed_at, changed_by, change_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, dataset_id, new_version,
                self._columns_to_json(new_columns),
                now, changed_by, change_description
            ))

            # Update dataset schema version
            cursor.execute("""
                UPDATE datasets
                SET schema_version = ?, updated_at = ?
                WHERE dataset_id = ?
            """, (new_version, now, dataset_id))

            # Delete old columns for this dataset
            cursor.execute("""
                DELETE FROM columns WHERE dataset_id = ?
            """, (dataset_id,))

            # Insert new columns
            for idx, col in enumerate(new_columns):
                column_id = f"{dataset_id}_col_{idx}_v{new_version}"
                cursor.execute("""
                    INSERT INTO columns (
                        column_id, dataset_id, schema_version, column_name,
                        data_type, nullable, pii_type, position, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    column_id, dataset_id, new_version, col['name'],
                    col['type'], col.get('nullable', True),
                    col.get('pii', 'none'), idx,
                    self._dict_to_json(col.get('metadata', {}))
                ))

            self.conn.commit()
            logger.info(f"Schema evolved to version {new_version} for {dataset_id}")

            return new_version, changes

        except Exception as e:
            logger.error(f"Failed to evolve schema: {e}")
            self.conn.rollback()
            raise

    def compare_schemas(
        self,
        old_columns: List[Dict[str, Any]],
        new_columns: List[Dict[str, Any]]
    ) -> List[SchemaChange]:
        """
        Compare two schemas and detect changes

        Args:
            old_columns: Old column definitions
            new_columns: New column definitions

        Returns:
            List of detected changes
        """
        changes = []

        # Build column maps
        old_map = {col['column_name']: col for col in old_columns}
        new_map = {col['name'] if 'name' in col else col['column_name']: col for col in new_columns}

        old_names = set(old_map.keys())
        new_names = set(new_map.keys())

        # Detect removed columns
        removed = old_names - new_names
        for col_name in removed:
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                severity=SeverityLevel.BREAKING,
                column_name=col_name,
                old_value=old_map[col_name]['data_type'],
                new_value=None,
                description=f"Column '{col_name}' was removed",
                impact="Consumers reading this column will fail"
            ))

        # Detect added columns
        added = new_names - old_names
        for col_name in added:
            new_col = new_map[col_name]
            col_type = new_col.get('type') or new_col.get('data_type')
            nullable = new_col.get('nullable', True)

            severity = SeverityLevel.MINOR if nullable else SeverityLevel.MAJOR

            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                severity=severity,
                column_name=col_name,
                old_value=None,
                new_value=col_type,
                description=f"Column '{col_name}' was added ({col_type}, nullable={nullable})",
                impact="Backward compatible if nullable, may break writers if not"
            ))

        # Detect changed columns
        common = old_names & new_names
        for col_name in common:
            old_col = old_map[col_name]
            new_col = new_map[col_name]

            # Normalize keys
            old_type = old_col.get('data_type') or old_col.get('type')
            new_type = new_col.get('type') or new_col.get('data_type')
            old_nullable = old_col.get('nullable', True)
            new_nullable = new_col.get('nullable', True)
            old_pii = old_col.get('pii_type') or old_col.get('pii', 'none')
            new_pii = new_col.get('pii') or new_col.get('pii_type', 'none')

            # Type change
            if old_type != new_type:
                severity = self._determine_type_change_severity(old_type, new_type)
                changes.append(SchemaChange(
                    change_type=ChangeType.TYPE_CHANGED,
                    severity=severity,
                    column_name=col_name,
                    old_value=old_type,
                    new_value=new_type,
                    description=f"Column '{col_name}' type changed from {old_type} to {new_type}",
                    impact=self._get_type_change_impact(old_type, new_type)
                ))

            # Nullable change
            if old_nullable != new_nullable:
                severity = SeverityLevel.BREAKING if not new_nullable else SeverityLevel.MINOR
                changes.append(SchemaChange(
                    change_type=ChangeType.NULLABLE_CHANGED,
                    severity=severity,
                    column_name=col_name,
                    old_value=old_nullable,
                    new_value=new_nullable,
                    description=f"Column '{col_name}' nullable changed from {old_nullable} to {new_nullable}",
                    impact="Breaking if changed to NOT NULL, safe if changed to NULL"
                ))

            # PII change
            if old_pii != new_pii:
                changes.append(SchemaChange(
                    change_type=ChangeType.PII_CHANGED,
                    severity=SeverityLevel.MAJOR,
                    column_name=col_name,
                    old_value=old_pii,
                    new_value=new_pii,
                    description=f"Column '{col_name}' PII classification changed from {old_pii} to {new_pii}",
                    impact="May affect data governance and compliance"
                ))

        return changes

    def _determine_type_change_severity(self, old_type: str, new_type: str) -> SeverityLevel:
        """Determine severity of type change"""
        # Define compatible type conversions
        compatible_conversions = {
            ('integer', 'float'): SeverityLevel.MINOR,
            ('integer', 'string'): SeverityLevel.MINOR,
            ('float', 'string'): SeverityLevel.MINOR,
            ('date', 'datetime'): SeverityLevel.MINOR,
            ('date', 'string'): SeverityLevel.MINOR,
            ('datetime', 'string'): SeverityLevel.MINOR,
        }

        # Check if conversion is compatible
        key = (old_type.lower(), new_type.lower())
        if key in compatible_conversions:
            return compatible_conversions[key]

        # Narrowing conversions are breaking
        narrowing = [
            ('string', 'integer'),
            ('string', 'float'),
            ('string', 'date'),
            ('string', 'datetime'),
            ('float', 'integer'),
            ('datetime', 'date'),
        ]

        if key in narrowing:
            return SeverityLevel.BREAKING

        # Other conversions are major
        return SeverityLevel.MAJOR

    def _get_type_change_impact(self, old_type: str, new_type: str) -> str:
        """Get impact description for type change"""
        narrowing = [
            ('string', 'integer'),
            ('string', 'float'),
            ('float', 'integer'),
        ]

        key = (old_type.lower(), new_type.lower())
        if key in narrowing:
            return f"BREAKING: Cannot safely convert {old_type} to {new_type}, data loss possible"

        widening = [
            ('integer', 'float'),
            ('integer', 'string'),
            ('date', 'datetime'),
        ]

        if key in widening:
            return f"Safe: {old_type} can be widened to {new_type}"

        return f"May require data transformation from {old_type} to {new_type}"

    def _generate_change_description(self, changes: List[SchemaChange]) -> str:
        """Generate human-readable change description"""
        if not changes:
            return "No changes"

        summary = []

        by_type = {}
        for change in changes:
            change_type = change.change_type.value
            if change_type not in by_type:
                by_type[change_type] = []
            by_type[change_type].append(change.column_name)

        for change_type, columns in by_type.items():
            count = len(columns)
            if count == 1:
                summary.append(f"{change_type}: {columns[0]}")
            else:
                summary.append(f"{change_type}: {count} columns")

        return "; ".join(summary)

    def get_schema_history(self, dataset_id: str) -> List[SchemaVersion]:
        """
        Get complete schema history for a dataset

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of schema versions ordered by version number
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM schema_versions
            WHERE dataset_id = ?
            ORDER BY schema_version DESC
        """, (dataset_id,))

        versions = []
        for row in cursor.fetchall():
            versions.append(SchemaVersion(
                version_id=row['version_id'],
                dataset_id=row['dataset_id'],
                version_number=row['schema_version'],
                columns=self._json_to_columns(row['columns']),
                changed_at=row['changed_at'],
                changed_by=row['changed_by'],
                change_description=row['change_description']
            ))

        return versions

    def get_version_diff(
        self,
        dataset_id: str,
        version1: int,
        version2: int
    ) -> List[SchemaChange]:
        """
        Get differences between two schema versions

        Args:
            dataset_id: Dataset identifier
            version1: First version number
            version2: Second version number

        Returns:
            List of changes
        """
        cursor = self.conn.cursor()

        # Get both versions
        cursor.execute("""
            SELECT columns FROM schema_versions
            WHERE dataset_id = ? AND schema_version = ?
        """, (dataset_id, version1))
        row1 = cursor.fetchone()

        cursor.execute("""
            SELECT columns FROM schema_versions
            WHERE dataset_id = ? AND schema_version = ?
        """, (dataset_id, version2))
        row2 = cursor.fetchone()

        if not row1 or not row2:
            raise ValueError(f"Version not found for dataset {dataset_id}")

        columns1 = self._json_to_columns(row1['columns'])
        columns2 = self._json_to_columns(row2['columns'])

        return self.compare_schemas(columns1, columns2)

    def analyze_impact(
        self,
        dataset_id: str,
        proposed_columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze impact of proposed schema changes

        Args:
            dataset_id: Dataset identifier
            proposed_columns: Proposed new schema

        Returns:
            Impact analysis report
        """
        dataset = self.catalog.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        current_columns = dataset['columns']
        changes = self.compare_schemas(current_columns, proposed_columns)

        # Count by severity
        severity_counts = {
            SeverityLevel.BREAKING: 0,
            SeverityLevel.MAJOR: 0,
            SeverityLevel.MINOR: 0,
            SeverityLevel.PATCH: 0
        }

        for change in changes:
            severity_counts[change.severity] += 1

        # Get downstream dependencies
        lineage = self.catalog.get_lineage_graph(dataset_id, depth=1)
        downstream_datasets = [
            node for node in lineage['nodes']
            if node['id'] != dataset_id
        ]

        # Assess risk level
        risk_level = "LOW"
        if severity_counts[SeverityLevel.BREAKING] > 0:
            risk_level = "CRITICAL"
        elif severity_counts[SeverityLevel.MAJOR] > 0:
            risk_level = "HIGH"
        elif severity_counts[SeverityLevel.MINOR] > 0:
            risk_level = "MEDIUM"

        return {
            'risk_level': risk_level,
            'total_changes': len(changes),
            'severity_breakdown': {k.value: v for k, v in severity_counts.items()},
            'changes': [
                {
                    'type': c.change_type.value,
                    'severity': c.severity.value,
                    'column': c.column_name,
                    'description': c.description,
                    'impact': c.impact
                }
                for c in changes
            ],
            'affected_datasets': len(downstream_datasets),
            'downstream_datasets': [d['name'] for d in downstream_datasets],
            'recommendations': self._generate_recommendations(changes, downstream_datasets)
        }

    def _generate_recommendations(
        self,
        changes: List[SchemaChange],
        downstream_datasets: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on changes"""
        recommendations = []

        breaking_changes = [c for c in changes if c.severity == SeverityLevel.BREAKING]
        if breaking_changes:
            recommendations.append(
                "CRITICAL: Breaking changes detected. Coordinate with downstream consumers."
            )
            recommendations.append(
                "Consider creating a new version of the dataset instead of modifying in-place."
            )

        if downstream_datasets:
            recommendations.append(
                f"Notify owners of {len(downstream_datasets)} downstream datasets about changes."
            )

        added_not_null = [
            c for c in changes
            if c.change_type == ChangeType.COLUMN_ADDED and c.severity == SeverityLevel.MAJOR
        ]
        if added_not_null:
            recommendations.append(
                "Added non-nullable columns. Ensure default values or backfill strategy."
            )

        return recommendations

    def _columns_to_json(self, columns: List[Dict[str, Any]]) -> str:
        """Convert columns to JSON string"""
        import json
        return json.dumps(columns)

    def _json_to_columns(self, json_str: str) -> List[Dict[str, Any]]:
        """Convert JSON string to columns"""
        import json
        return json.loads(json_str)

    def _dict_to_json(self, data: Dict) -> str:
        """Convert dict to JSON string"""
        import json
        return json.dumps(data)
