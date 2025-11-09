"""
NUIC Catalog Engine - Core database-backed catalog system

Provides comprehensive catalog management with:
- SQLite/PostgreSQL database backend
- Dataset registration and discovery
- Schema versioning and evolution
- Lineage tracking
- Quality metrics time series
- Auto-tagging and metadata management
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DatasetStatus(Enum):
    """Dataset lifecycle status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    DELETED = "deleted"


class LineageType(Enum):
    """Types of lineage relationships"""
    DERIVED_FROM = "derived_from"
    TRANSFORMED_TO = "transformed_to"
    JOINED_WITH = "joined_with"
    AGGREGATED_FROM = "aggregated_from"
    FILTERED_FROM = "filtered_from"


@dataclass
class CatalogEntry:
    """Dataset catalog entry"""
    dataset_id: str
    dataset_name: str
    schema_version: int
    quality_score: float
    row_count: int
    size_bytes: int
    storage_location: str
    routing_path: str
    status: str
    created_at: str
    updated_at: str
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class SchemaColumn:
    """Schema column definition"""
    column_id: str
    dataset_id: str
    schema_version: int
    column_name: str
    data_type: str
    nullable: bool
    pii_type: str
    position: int
    metadata: Dict[str, Any]


@dataclass
class QualityMetric:
    """Quality metric time series entry"""
    metric_id: str
    dataset_id: str
    measured_at: str
    overall_score: float
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    uniqueness: float
    validity: float
    issues_found: int
    metadata: Dict[str, Any]


class NUICEngine:
    """
    NeuroLake Unified Intelligence Catalog Engine

    Central catalog system with database backend for managing all
    datasets, schemas, lineage, and quality metrics.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize NUIC Engine

        Args:
            db_path: Path to SQLite database (defaults to C:/NeuroLake/catalog/nuic.db)
        """
        self.db_path = db_path or "C:/NeuroLake/catalog/nuic.db"
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """Create database schema if not exists"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Datasets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                schema_version INTEGER DEFAULT 1,
                quality_score REAL,
                row_count INTEGER,
                size_bytes INTEGER,
                storage_location TEXT,
                routing_path TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags TEXT,  -- JSON array
                metadata TEXT  -- JSON object
            )
        """)

        # Create index on dataset_name for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dataset_name
            ON datasets(dataset_name)
        """)

        # Schema versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                columns TEXT NOT NULL,  -- JSON array
                changed_at TEXT NOT NULL,
                changed_by TEXT,
                change_description TEXT,
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            )
        """)

        # Columns table (current schema)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS columns (
                column_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                column_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                nullable BOOLEAN DEFAULT 1,
                pii_type TEXT DEFAULT 'none',
                position INTEGER,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            )
        """)

        # Create index for column lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_columns_dataset
            ON columns(dataset_id, schema_version)
        """)

        # Lineage table (graph edges)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lineage (
                lineage_id TEXT PRIMARY KEY,
                source_dataset_id TEXT NOT NULL,
                target_dataset_id TEXT NOT NULL,
                lineage_type TEXT NOT NULL,
                transformation_code TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (source_dataset_id) REFERENCES datasets(dataset_id),
                FOREIGN KEY (target_dataset_id) REFERENCES datasets(dataset_id)
            )
        """)

        # Column-level lineage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS column_lineage (
                column_lineage_id TEXT PRIMARY KEY,
                lineage_id TEXT NOT NULL,
                source_column TEXT NOT NULL,
                target_column TEXT NOT NULL,
                transformation TEXT,
                FOREIGN KEY (lineage_id) REFERENCES lineage(lineage_id)
            )
        """)

        # Quality metrics time series
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                metric_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                measured_at TEXT NOT NULL,
                overall_score REAL,
                completeness REAL,
                accuracy REAL,
                consistency REAL,
                timeliness REAL,
                uniqueness REAL,
                validity REAL,
                issues_found INTEGER,
                metadata TEXT,  -- JSON object
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            )
        """)

        # Create index for time series queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_metrics_dataset_time
            ON quality_metrics(dataset_id, measured_at DESC)
        """)

        # Tags index for fast tag-based searches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dataset_tags (
                dataset_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (dataset_id, tag),
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dataset_tags_tag
            ON dataset_tags(tag)
        """)

        self.conn.commit()
        logger.info(f"NUIC database initialized at {self.db_path}")

    def register_dataset(
        self,
        dataset_id: str,
        dataset_name: str,
        schema_columns: List[Dict[str, Any]],
        quality_score: float,
        row_count: int,
        size_bytes: int,
        storage_location: str,
        routing_path: str,
        tags: List[str],
        metadata: Optional[Dict] = None,
        user: str = "system"
    ) -> bool:
        """
        Register a new dataset in the catalog

        Args:
            dataset_id: Unique dataset identifier
            dataset_name: Human-readable name
            schema_columns: List of column definitions
            quality_score: Overall quality score
            row_count: Number of rows
            size_bytes: Size in bytes
            storage_location: Physical storage path
            routing_path: Processing path (express/standard/quality/enrichment)
            tags: List of tags
            metadata: Additional metadata
            user: User who registered the dataset

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            # Insert dataset
            cursor.execute("""
                INSERT INTO datasets (
                    dataset_id, dataset_name, schema_version, quality_score,
                    row_count, size_bytes, storage_location, routing_path,
                    status, created_at, updated_at, tags, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id, dataset_name, 1, quality_score,
                row_count, size_bytes, storage_location, routing_path,
                DatasetStatus.ACTIVE.value, now, now,
                json.dumps(tags), json.dumps(metadata or {})
            ))

            # Insert tags
            for tag in tags:
                cursor.execute("""
                    INSERT OR IGNORE INTO dataset_tags (dataset_id, tag)
                    VALUES (?, ?)
                """, (dataset_id, tag))

            # Insert columns
            for idx, col in enumerate(schema_columns):
                column_id = f"{dataset_id}_col_{idx}"
                cursor.execute("""
                    INSERT INTO columns (
                        column_id, dataset_id, schema_version, column_name,
                        data_type, nullable, pii_type, position, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    column_id, dataset_id, 1, col['name'],
                    col['type'], col.get('nullable', True),
                    col.get('pii', 'none'), idx,
                    json.dumps(col.get('metadata', {}))
                ))

            # Create initial schema version
            version_id = f"{dataset_id}_v1"
            cursor.execute("""
                INSERT INTO schema_versions (
                    version_id, dataset_id, schema_version, columns,
                    changed_at, changed_by, change_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, dataset_id, 1, json.dumps(schema_columns),
                now, user, "Initial schema"
            ))

            self.conn.commit()
            logger.info(f"Registered dataset: {dataset_name} ({dataset_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to register dataset: {e}")
            self.conn.rollback()
            return False

    def record_quality_metric(
        self,
        dataset_id: str,
        overall_score: float,
        dimension_scores: Dict[str, float],
        issues_found: int,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Record a quality metric measurement

        Args:
            dataset_id: Dataset identifier
            overall_score: Overall quality score
            dimension_scores: Scores for each quality dimension
            issues_found: Number of issues detected
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            metric_id = f"{dataset_id}_qm_{now.replace(':', '').replace('-', '')}"

            cursor.execute("""
                INSERT INTO quality_metrics (
                    metric_id, dataset_id, measured_at, overall_score,
                    completeness, accuracy, consistency, timeliness,
                    uniqueness, validity, issues_found, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_id, dataset_id, now, overall_score,
                dimension_scores.get('completeness', 0),
                dimension_scores.get('accuracy', 0),
                dimension_scores.get('consistency', 0),
                dimension_scores.get('timeliness', 0),
                dimension_scores.get('uniqueness', 0),
                dimension_scores.get('validity', 0),
                issues_found,
                json.dumps(metadata or {})
            ))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to record quality metric: {e}")
            self.conn.rollback()
            return False

    def track_lineage(
        self,
        source_dataset_id: str,
        target_dataset_id: str,
        lineage_type: LineageType,
        transformation_code: Optional[str] = None,
        column_mappings: Optional[List[Tuple[str, str, str]]] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Track lineage between datasets

        Args:
            source_dataset_id: Source dataset ID
            target_dataset_id: Target dataset ID
            lineage_type: Type of lineage relationship
            transformation_code: Transformation code applied
            column_mappings: List of (source_col, target_col, transformation) tuples
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            lineage_id = f"lineage_{source_dataset_id}_{target_dataset_id}_{now.replace(':', '').replace('-', '')}"

            # Insert lineage edge
            cursor.execute("""
                INSERT INTO lineage (
                    lineage_id, source_dataset_id, target_dataset_id,
                    lineage_type, transformation_code, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                lineage_id, source_dataset_id, target_dataset_id,
                lineage_type.value, transformation_code, now,
                json.dumps(metadata or {})
            ))

            # Insert column-level lineage if provided
            if column_mappings:
                for source_col, target_col, transformation in column_mappings:
                    col_lineage_id = f"{lineage_id}_{source_col}_{target_col}"
                    cursor.execute("""
                        INSERT INTO column_lineage (
                            column_lineage_id, lineage_id, source_column,
                            target_column, transformation
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        col_lineage_id, lineage_id, source_col,
                        target_col, transformation
                    ))

            self.conn.commit()
            logger.info(f"Tracked lineage: {source_dataset_id} -> {target_dataset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to track lineage: {e}")
            self.conn.rollback()
            return False

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Get dataset by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,))
        row = cursor.fetchone()

        if row:
            dataset = dict(row)
            dataset['tags'] = json.loads(dataset['tags'])
            dataset['metadata'] = json.loads(dataset['metadata'])

            # Get columns
            cursor.execute("""
                SELECT * FROM columns
                WHERE dataset_id = ? AND schema_version = ?
                ORDER BY position
            """, (dataset_id, dataset['schema_version']))

            columns = []
            for col_row in cursor.fetchall():
                col = dict(col_row)
                col['metadata'] = json.loads(col['metadata'])
                columns.append(col)

            dataset['columns'] = columns
            return dataset

        return None

    def search_datasets(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_quality: Optional[float] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for datasets

        Args:
            query: Search query (searches name)
            tags: Filter by tags
            min_quality: Minimum quality score
            status: Filter by status
            limit: Maximum results

        Returns:
            List of matching datasets
        """
        cursor = self.conn.cursor()

        sql = "SELECT * FROM datasets WHERE 1=1"
        params = []

        if query:
            sql += " AND dataset_name LIKE ?"
            params.append(f"%{query}%")

        if min_quality is not None:
            sql += " AND quality_score >= ?"
            params.append(min_quality)

        if status:
            sql += " AND status = ?"
            params.append(status)

        if tags:
            # Join with dataset_tags for tag filtering
            tag_placeholders = ','.join(['?'] * len(tags))
            sql = f"""
                SELECT DISTINCT d.* FROM datasets d
                JOIN dataset_tags dt ON d.dataset_id = dt.dataset_id
                WHERE dt.tag IN ({tag_placeholders})
            """
            params = tags

            if query:
                sql += " AND d.dataset_name LIKE ?"
                params.append(f"%{query}%")
            if min_quality is not None:
                sql += " AND d.quality_score >= ?"
                params.append(min_quality)
            if status:
                sql += " AND d.status = ?"
                params.append(status)

        sql += f" ORDER BY updated_at DESC LIMIT {limit}"

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            dataset = dict(row)
            dataset['tags'] = json.loads(dataset['tags'])
            dataset['metadata'] = json.loads(dataset['metadata'])
            results.append(dataset)

        return results

    def get_lineage_graph(self, dataset_id: str, depth: int = 3) -> Dict:
        """
        Get lineage graph for a dataset

        Args:
            dataset_id: Dataset identifier
            depth: How many levels to traverse

        Returns:
            Graph structure with nodes and edges
        """
        cursor = self.conn.cursor()

        nodes = {}
        edges = []
        visited = set()

        def traverse(current_id, current_depth, direction='both'):
            if current_depth > depth or current_id in visited:
                return

            visited.add(current_id)

            # Add node
            dataset = self.get_dataset(current_id)
            if dataset:
                nodes[current_id] = {
                    'id': current_id,
                    'name': dataset['dataset_name'],
                    'quality_score': dataset['quality_score'],
                    'status': dataset['status']
                }

            # Get upstream lineage (sources)
            if direction in ['both', 'upstream']:
                cursor.execute("""
                    SELECT * FROM lineage WHERE target_dataset_id = ?
                """, (current_id,))

                for row in cursor.fetchall():
                    lineage = dict(row)
                    edges.append({
                        'source': lineage['source_dataset_id'],
                        'target': lineage['target_dataset_id'],
                        'type': lineage['lineage_type']
                    })
                    traverse(lineage['source_dataset_id'], current_depth + 1, 'upstream')

            # Get downstream lineage (targets)
            if direction in ['both', 'downstream']:
                cursor.execute("""
                    SELECT * FROM lineage WHERE source_dataset_id = ?
                """, (current_id,))

                for row in cursor.fetchall():
                    lineage = dict(row)
                    edges.append({
                        'source': lineage['source_dataset_id'],
                        'target': lineage['target_dataset_id'],
                        'type': lineage['lineage_type']
                    })
                    traverse(lineage['target_dataset_id'], current_depth + 1, 'downstream')

        traverse(dataset_id, 0)

        return {
            'nodes': list(nodes.values()),
            'edges': edges
        }

    def get_quality_time_series(
        self,
        dataset_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get quality metrics time series for a dataset

        Args:
            dataset_id: Dataset identifier
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum records

        Returns:
            List of quality metrics ordered by time
        """
        cursor = self.conn.cursor()

        sql = "SELECT * FROM quality_metrics WHERE dataset_id = ?"
        params = [dataset_id]

        if start_date:
            sql += " AND measured_at >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND measured_at <= ?"
            params.append(end_date)

        sql += f" ORDER BY measured_at DESC LIMIT {limit}"

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            metric = dict(row)
            metric['metadata'] = json.loads(metric['metadata'])
            results.append(metric)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM datasets")
        total_datasets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM datasets WHERE status = 'active'")
        active_datasets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT tag) FROM dataset_tags")
        total_tags = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM lineage")
        total_lineage = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM quality_metrics")
        total_quality_metrics = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(quality_score) FROM datasets WHERE status = 'active'")
        avg_quality = cursor.fetchone()[0] or 0

        return {
            'total_datasets': total_datasets,
            'active_datasets': active_datasets,
            'total_tags': total_tags,
            'total_lineage_edges': total_lineage,
            'total_quality_measurements': total_quality_metrics,
            'average_quality_score': avg_quality,
            'db_path': self.db_path
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("NUIC database connection closed")

    def __enter__(self):
        """Context manager entry - return self for use in 'with' statement"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed"""
        self.close()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Destructor - ensure connection is closed on garbage collection"""
        try:
            self.close()
        except Exception:
            # Silently ignore errors during cleanup
            pass
