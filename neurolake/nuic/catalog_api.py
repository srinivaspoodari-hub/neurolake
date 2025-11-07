"""
NUIC Catalog Query API

Advanced query and discovery API for the catalog with:
- Full-text search
- Faceted search
- Dataset recommendations
- Metadata aggregations
- Advanced filters
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchFilter:
    """Search filter specification"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, like, between
    value: Any


@dataclass
class SearchResult:
    """Search result with metadata"""
    dataset_id: str
    dataset_name: str
    description: str
    quality_score: float
    row_count: int
    tags: List[str]
    relevance_score: float
    snippet: str


class CatalogQueryAPI:
    """
    Advanced query and discovery API for NUIC

    Capabilities:
    - Full-text search across metadata
    - Faceted search with aggregations
    - Dataset recommendations
    - Similarity search
    - Advanced filtering
    - Query statistics
    """

    def __init__(self, catalog_engine):
        """
        Initialize Catalog Query API

        Args:
            catalog_engine: NUICEngine instance
        """
        self.catalog = catalog_engine
        self.conn = catalog_engine.conn

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[List[SearchFilter]] = None,
        tags: Optional[List[str]] = None,
        quality_range: Optional[Tuple[float, float]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        sort_by: str = 'relevance',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Advanced search with multiple filters

        Args:
            query: Text search query
            filters: List of search filters
            tags: Filter by tags
            quality_range: (min, max) quality score
            date_range: (start, end) date range
            sort_by: Sort field (relevance, quality, updated, name)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Search results with facets and pagination
        """
        cursor = self.conn.cursor()

        # Build SQL query
        sql_parts = ["SELECT d.* FROM datasets d"]
        joins = []
        where_clauses = ["1=1"]
        params = []

        # Text search
        if query:
            where_clauses.append("""
                (d.dataset_name LIKE ? OR
                 d.metadata LIKE ? OR
                 d.tags LIKE ?)
            """)
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])

        # Tag filter
        if tags:
            joins.append("JOIN dataset_tags dt ON d.dataset_id = dt.dataset_id")
            tag_placeholders = ','.join(['?'] * len(tags))
            where_clauses.append(f"dt.tag IN ({tag_placeholders})")
            params.extend(tags)

        # Quality range
        if quality_range:
            min_q, max_q = quality_range
            where_clauses.append("d.quality_score BETWEEN ? AND ?")
            params.extend([min_q, max_q])

        # Date range
        if date_range:
            start, end = date_range
            where_clauses.append("d.updated_at BETWEEN ? AND ?")
            params.extend([start, end])

        # Custom filters
        if filters:
            for f in filters:
                clause, filter_params = self._build_filter_clause(f)
                where_clauses.append(clause)
                params.extend(filter_params)

        # Construct query
        sql = sql_parts[0]
        if joins:
            sql += " " + " ".join(joins)
        sql += " WHERE " + " AND ".join(where_clauses)

        # Add GROUP BY if using joins
        if joins:
            sql += " GROUP BY d.dataset_id"

        # Sort
        if sort_by == 'quality':
            sql += " ORDER BY d.quality_score DESC"
        elif sort_by == 'updated':
            sql += " ORDER BY d.updated_at DESC"
        elif sort_by == 'name':
            sql += " ORDER BY d.dataset_name ASC"
        else:  # relevance (just use quality for now)
            sql += " ORDER BY d.quality_score DESC"

        # Get total count before pagination
        count_sql = f"SELECT COUNT(*) FROM ({sql}) AS subquery"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        # Add pagination
        sql += f" LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Execute search
        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            import json
            results.append({
                'dataset_id': row['dataset_id'],
                'dataset_name': row['dataset_name'],
                'quality_score': row['quality_score'],
                'row_count': row['row_count'],
                'size_bytes': row['size_bytes'],
                'storage_location': row['storage_location'],
                'routing_path': row['routing_path'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'tags': json.loads(row['tags']),
                'metadata': json.loads(row['metadata'])
            })

        # Get facets
        facets = self._compute_facets(query, filters, tags, quality_range, date_range)

        return {
            'results': results,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'facets': facets,
            'query': query
        }

    def _build_filter_clause(self, filter: SearchFilter) -> Tuple[str, List]:
        """Build SQL clause for a filter"""
        field = filter.field
        op = filter.operator
        value = filter.value

        if op == 'eq':
            return f"d.{field} = ?", [value]
        elif op == 'ne':
            return f"d.{field} != ?", [value]
        elif op == 'gt':
            return f"d.{field} > ?", [value]
        elif op == 'lt':
            return f"d.{field} < ?", [value]
        elif op == 'gte':
            return f"d.{field} >= ?", [value]
        elif op == 'lte':
            return f"d.{field} <= ?", [value]
        elif op == 'like':
            return f"d.{field} LIKE ?", [f"%{value}%"]
        elif op == 'in':
            placeholders = ','.join(['?'] * len(value))
            return f"d.{field} IN ({placeholders})", value
        elif op == 'between':
            return f"d.{field} BETWEEN ? AND ?", value
        else:
            raise ValueError(f"Unknown operator: {op}")

    def _compute_facets(
        self,
        query: Optional[str],
        filters: Optional[List[SearchFilter]],
        tags: Optional[List[str]],
        quality_range: Optional[Tuple[float, float]],
        date_range: Optional[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Compute facets for search results"""
        cursor = self.conn.cursor()

        facets = {}

        # Tag facets
        cursor.execute("""
            SELECT tag, COUNT(*) as count
            FROM dataset_tags
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 20
        """)
        facets['tags'] = [
            {'tag': row['tag'], 'count': row['count']}
            for row in cursor.fetchall()
        ]

        # Quality distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score >= 0.9 THEN 'high'
                    WHEN quality_score >= 0.7 THEN 'medium'
                    ELSE 'low'
                END as quality_tier,
                COUNT(*) as count
            FROM datasets
            GROUP BY quality_tier
        """)
        facets['quality_distribution'] = {
            row['quality_tier']: row['count']
            for row in cursor.fetchall()
        }

        # Routing path distribution
        cursor.execute("""
            SELECT routing_path, COUNT(*) as count
            FROM datasets
            GROUP BY routing_path
        """)
        facets['routing_paths'] = {
            row['routing_path']: row['count']
            for row in cursor.fetchall()
        }

        # Status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM datasets
            GROUP BY status
        """)
        facets['status'] = {
            row['status']: row['count']
            for row in cursor.fetchall()
        }

        return facets

    def recommend_datasets(
        self,
        dataset_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend similar datasets

        Uses:
        - Tag similarity
        - Schema similarity
        - Quality similarity
        - Lineage relationships

        Args:
            dataset_id: Dataset to find recommendations for
            limit: Maximum recommendations

        Returns:
            List of recommended datasets with scores
        """
        cursor = self.conn.cursor()

        # Get source dataset
        source = self.catalog.get_dataset(dataset_id)
        if not source:
            return []

        source_tags = set(source['tags'])
        source_quality = source['quality_score']

        # Score all other datasets
        cursor.execute("""
            SELECT dataset_id, dataset_name, quality_score, tags
            FROM datasets
            WHERE dataset_id != ? AND status = 'active'
        """, (dataset_id,))

        recommendations = []
        for row in cursor.fetchall():
            import json
            candidate_tags = set(json.loads(row['tags']))

            # Tag similarity (Jaccard index)
            tag_similarity = len(source_tags & candidate_tags) / max(len(source_tags | candidate_tags), 1)

            # Quality similarity
            quality_diff = abs(source_quality - row['quality_score'])
            quality_similarity = 1.0 - min(quality_diff, 1.0)

            # Check if in lineage
            lineage_bonus = 0.0
            cursor.execute("""
                SELECT COUNT(*) FROM lineage
                WHERE (source_dataset_id = ? AND target_dataset_id = ?)
                   OR (source_dataset_id = ? AND target_dataset_id = ?)
            """, (dataset_id, row['dataset_id'], row['dataset_id'], dataset_id))
            if cursor.fetchone()[0] > 0:
                lineage_bonus = 0.3

            # Combined score
            score = (tag_similarity * 0.5) + (quality_similarity * 0.2) + lineage_bonus

            if score > 0:
                recommendations.append({
                    'dataset_id': row['dataset_id'],
                    'dataset_name': row['dataset_name'],
                    'quality_score': row['quality_score'],
                    'tags': json.loads(row['tags']),
                    'recommendation_score': round(score, 3),
                    'reason': self._get_recommendation_reason(tag_similarity, quality_similarity, lineage_bonus)
                })

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:limit]

    def _get_recommendation_reason(
        self,
        tag_sim: float,
        quality_sim: float,
        lineage_bonus: float
    ) -> str:
        """Generate reason for recommendation"""
        reasons = []

        if tag_sim > 0.5:
            reasons.append("similar tags")
        if quality_sim > 0.8:
            reasons.append("similar quality")
        if lineage_bonus > 0:
            reasons.append("related in lineage")

        return ", ".join(reasons) if reasons else "general similarity"

    def get_dataset_insights(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get comprehensive insights about a dataset

        Args:
            dataset_id: Dataset identifier

        Returns:
            Insights dictionary
        """
        cursor = self.conn.cursor()

        dataset = self.catalog.get_dataset(dataset_id)
        if not dataset:
            return {}

        # Get quality trend
        cursor.execute("""
            SELECT measured_at, overall_score
            FROM quality_metrics
            WHERE dataset_id = ?
            ORDER BY measured_at DESC
            LIMIT 10
        """, (dataset_id,))

        quality_history = [
            {'timestamp': row['measured_at'], 'score': row['overall_score']}
            for row in cursor.fetchall()
        ]

        # Calculate quality trend
        if len(quality_history) >= 2:
            recent_avg = sum(q['score'] for q in quality_history[:3]) / min(len(quality_history), 3)
            older_avg = sum(q['score'] for q in quality_history[-3:]) / min(len(quality_history), 3)
            quality_trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        else:
            quality_trend = "insufficient_data"

        # Get lineage stats
        cursor.execute("""
            SELECT COUNT(*) FROM lineage WHERE target_dataset_id = ?
        """, (dataset_id,))
        upstream_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM lineage WHERE source_dataset_id = ?
        """, (dataset_id,))
        downstream_count = cursor.fetchone()[0]

        # Get schema evolution
        cursor.execute("""
            SELECT COUNT(*) FROM schema_versions WHERE dataset_id = ?
        """, (dataset_id,))
        schema_versions = cursor.fetchone()[0]

        # Get update frequency
        cursor.execute("""
            SELECT created_at, updated_at FROM datasets WHERE dataset_id = ?
        """, (dataset_id,))
        row = cursor.fetchone()
        created = datetime.fromisoformat(row['created_at'])
        updated = datetime.fromisoformat(row['updated_at'])
        age_days = (datetime.now() - created).days
        days_since_update = (datetime.now() - updated).days

        return {
            'dataset_id': dataset_id,
            'dataset_name': dataset['dataset_name'],
            'quality': {
                'current_score': dataset['quality_score'],
                'trend': quality_trend,
                'history': quality_history
            },
            'lineage': {
                'upstream_count': upstream_count,
                'downstream_count': downstream_count,
                'total_dependencies': upstream_count + downstream_count
            },
            'schema': {
                'current_version': dataset['schema_version'],
                'total_versions': schema_versions,
                'column_count': len(dataset['columns'])
            },
            'usage': {
                'age_days': age_days,
                'days_since_update': days_since_update,
                'update_frequency': self._calculate_update_frequency(dataset_id)
            },
            'storage': {
                'row_count': dataset['row_count'],
                'size_bytes': dataset['size_bytes'],
                'size_mb': round(dataset['size_bytes'] / 1024 / 1024, 2),
                'routing_path': dataset['routing_path']
            },
            'tags': dataset['tags'],
            'status': dataset['status']
        }

    def _calculate_update_frequency(self, dataset_id: str) -> str:
        """Calculate how often dataset is updated"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT measured_at FROM quality_metrics
            WHERE dataset_id = ?
            ORDER BY measured_at DESC
            LIMIT 10
        """, (dataset_id,))

        measurements = [row['measured_at'] for row in cursor.fetchall()]

        if len(measurements) < 2:
            return "unknown"

        # Calculate average time between updates
        deltas = []
        for i in range(len(measurements) - 1):
            t1 = datetime.fromisoformat(measurements[i])
            t2 = datetime.fromisoformat(measurements[i + 1])
            deltas.append((t1 - t2).total_seconds())

        avg_delta = sum(deltas) / len(deltas)

        # Classify frequency
        if avg_delta < 3600:  # < 1 hour
            return "real-time"
        elif avg_delta < 86400:  # < 1 day
            return "hourly"
        elif avg_delta < 604800:  # < 1 week
            return "daily"
        elif avg_delta < 2592000:  # < 30 days
            return "weekly"
        else:
            return "monthly"

    def get_popular_datasets(
        self,
        period_days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most popular datasets based on lineage usage

        Args:
            period_days: Time period in days
            limit: Maximum results

        Returns:
            List of popular datasets
        """
        cursor = self.conn.cursor()

        since_date = (datetime.now() - timedelta(days=period_days)).isoformat()

        # Count lineage references
        cursor.execute("""
            SELECT
                d.dataset_id,
                d.dataset_name,
                d.quality_score,
                d.tags,
                COUNT(DISTINCT l.lineage_id) as usage_count
            FROM datasets d
            LEFT JOIN lineage l ON d.dataset_id = l.source_dataset_id OR d.dataset_id = l.target_dataset_id
            WHERE d.status = 'active'
            GROUP BY d.dataset_id
            ORDER BY usage_count DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            import json
            results.append({
                'dataset_id': row['dataset_id'],
                'dataset_name': row['dataset_name'],
                'quality_score': row['quality_score'],
                'tags': json.loads(row['tags']),
                'usage_count': row['usage_count']
            })

        return results

    def get_quality_leaders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get highest quality datasets

        Args:
            limit: Maximum results

        Returns:
            List of high-quality datasets
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT dataset_id, dataset_name, quality_score, row_count, tags
            FROM datasets
            WHERE status = 'active' AND quality_score IS NOT NULL
            ORDER BY quality_score DESC, row_count DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            import json
            results.append({
                'dataset_id': row['dataset_id'],
                'dataset_name': row['dataset_name'],
                'quality_score': row['quality_score'],
                'row_count': row['row_count'],
                'tags': json.loads(row['tags'])
            })

        return results

    def search_by_column(
        self,
        column_name: str,
        data_type: Optional[str] = None,
        pii_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search datasets by column characteristics

        Args:
            column_name: Column name pattern
            data_type: Filter by data type
            pii_type: Filter by PII classification
            limit: Maximum results

        Returns:
            List of datasets with matching columns
        """
        cursor = self.conn.cursor()

        sql = """
            SELECT DISTINCT d.dataset_id, d.dataset_name, d.quality_score,
                   c.column_name, c.data_type, c.pii_type
            FROM datasets d
            JOIN columns c ON d.dataset_id = c.dataset_id
            WHERE c.column_name LIKE ?
        """
        params = [f"%{column_name}%"]

        if data_type:
            sql += " AND c.data_type = ?"
            params.append(data_type)

        if pii_type:
            sql += " AND c.pii_type = ?"
            params.append(pii_type)

        sql += f" LIMIT {limit}"

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                'dataset_id': row['dataset_id'],
                'dataset_name': row['dataset_name'],
                'quality_score': row['quality_score'],
                'column_name': row['column_name'],
                'data_type': row['data_type'],
                'pii_type': row['pii_type']
            })

        return results

    def get_catalog_statistics(self) -> Dict[str, Any]:
        """Get comprehensive catalog statistics"""
        cursor = self.conn.cursor()

        stats = {}

        # Dataset counts
        cursor.execute("SELECT COUNT(*) FROM datasets")
        stats['total_datasets'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM datasets WHERE status = 'active'")
        stats['active_datasets'] = cursor.fetchone()[0]

        # Quality stats
        cursor.execute("""
            SELECT
                AVG(quality_score) as avg_quality,
                MIN(quality_score) as min_quality,
                MAX(quality_score) as max_quality
            FROM datasets WHERE status = 'active'
        """)
        row = cursor.fetchone()
        stats['quality_stats'] = {
            'average': row['avg_quality'] or 0,
            'min': row['min_quality'] or 0,
            'max': row['max_quality'] or 0
        }

        # Size stats
        cursor.execute("""
            SELECT
                SUM(row_count) as total_rows,
                SUM(size_bytes) as total_bytes
            FROM datasets WHERE status = 'active'
        """)
        row = cursor.fetchone()
        stats['size_stats'] = {
            'total_rows': row['total_rows'] or 0,
            'total_bytes': row['total_bytes'] or 0,
            'total_gb': round((row['total_bytes'] or 0) / 1024 / 1024 / 1024, 2)
        }

        # Lineage stats
        cursor.execute("SELECT COUNT(*) FROM lineage")
        stats['lineage_edges'] = cursor.fetchone()[0]

        # Quality metrics
        cursor.execute("SELECT COUNT(*) FROM quality_metrics")
        stats['quality_measurements'] = cursor.fetchone()[0]

        # Schema versions
        cursor.execute("SELECT COUNT(*) FROM schema_versions")
        stats['schema_versions'] = cursor.fetchone()[0]

        # Tags
        cursor.execute("SELECT COUNT(DISTINCT tag) FROM dataset_tags")
        stats['unique_tags'] = cursor.fetchone()[0]

        # Most common tags
        cursor.execute("""
            SELECT tag, COUNT(*) as count
            FROM dataset_tags
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_tags'] = [
            {'tag': row['tag'], 'count': row['count']}
            for row in cursor.fetchall()
        ]

        return stats