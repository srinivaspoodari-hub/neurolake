"""
Graph-Based Lineage System

Advanced lineage tracking with graph analytics, impact analysis, and dependency visualization.
Supports column-level lineage, critical path detection, and circular dependency detection.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ImpactScope(Enum):
    """Scope of impact analysis"""
    IMMEDIATE = "immediate"  # Direct dependencies only
    DOWNSTREAM = "downstream"  # All downstream datasets
    UPSTREAM = "upstream"  # All upstream datasets
    FULL = "full"  # Both upstream and downstream


@dataclass
class LineageNode:
    """Node in the lineage graph"""
    dataset_id: str
    dataset_name: str
    quality_score: float
    status: str
    schema_version: int
    depth: int
    distance: int  # Distance from root node


@dataclass
class LineageEdge:
    """Edge in the lineage graph"""
    source_id: str
    target_id: str
    lineage_type: str
    transformation_code: Optional[str]
    column_mappings: List[Tuple[str, str]]


@dataclass
class ImpactAnalysis:
    """Impact analysis result"""
    affected_datasets: List[str]
    affected_count: int
    critical_path: List[str]
    risk_score: float
    max_depth: int
    recommendations: List[str]


class LineageGraph:
    """
    Advanced graph-based lineage system

    Capabilities:
    - Multi-level lineage traversal
    - Impact analysis (upstream/downstream)
    - Critical path detection
    - Circular dependency detection
    - Column-level lineage tracking
    - Data freshness analysis
    """

    def __init__(self, catalog_engine):
        """
        Initialize Lineage Graph

        Args:
            catalog_engine: NUICEngine instance
        """
        self.catalog = catalog_engine
        self.conn = catalog_engine.conn

    def build_full_graph(self) -> Dict[str, Any]:
        """
        Build complete lineage graph for all datasets

        Returns:
            Full graph structure
        """
        cursor = self.conn.cursor()

        # Get all datasets
        cursor.execute("SELECT dataset_id, dataset_name, quality_score, status FROM datasets")
        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                'id': row['dataset_id'],
                'name': row['dataset_name'],
                'quality': row['quality_score'],
                'status': row['status']
            })

        # Get all lineage edges
        cursor.execute("SELECT * FROM lineage")
        edges = []
        for row in cursor.fetchall():
            edges.append({
                'source': row['source_dataset_id'],
                'target': row['target_dataset_id'],
                'type': row['lineage_type']
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }

    def get_upstream_lineage(
        self,
        dataset_id: str,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get all upstream dependencies (data sources)

        Args:
            dataset_id: Dataset identifier
            max_depth: Maximum traversal depth

        Returns:
            Upstream lineage graph
        """
        return self._traverse_lineage(
            dataset_id,
            direction='upstream',
            max_depth=max_depth
        )

    def get_downstream_lineage(
        self,
        dataset_id: str,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get all downstream dependencies (consumers)

        Args:
            dataset_id: Dataset identifier
            max_depth: Maximum traversal depth

        Returns:
            Downstream lineage graph
        """
        return self._traverse_lineage(
            dataset_id,
            direction='downstream',
            max_depth=max_depth
        )

    def _traverse_lineage(
        self,
        dataset_id: str,
        direction: str,
        max_depth: int
    ) -> Dict[str, Any]:
        """
        Traverse lineage graph in specified direction

        Args:
            dataset_id: Starting dataset
            direction: 'upstream' or 'downstream'
            max_depth: Maximum depth

        Returns:
            Lineage graph
        """
        cursor = self.conn.cursor()

        nodes = {}
        edges = []
        visited = set()

        def traverse(current_id: str, depth: int, distance: int):
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)

            # Get dataset info
            cursor.execute("""
                SELECT dataset_id, dataset_name, quality_score, status, schema_version
                FROM datasets WHERE dataset_id = ?
            """, (current_id,))

            row = cursor.fetchone()
            if row:
                nodes[current_id] = LineageNode(
                    dataset_id=row['dataset_id'],
                    dataset_name=row['dataset_name'],
                    quality_score=row['quality_score'] or 0,
                    status=row['status'],
                    schema_version=row['schema_version'],
                    depth=depth,
                    distance=distance
                )

            # Get lineage edges
            if direction == 'upstream':
                # Get sources (datasets this one depends on)
                cursor.execute("""
                    SELECT l.*,
                           (SELECT GROUP_CONCAT(source_column || '->' || target_column)
                            FROM column_lineage cl
                            WHERE cl.lineage_id = l.lineage_id) as column_mappings
                    FROM lineage l
                    WHERE l.target_dataset_id = ?
                """, (current_id,))
            else:
                # Get consumers (datasets that depend on this)
                cursor.execute("""
                    SELECT l.*,
                           (SELECT GROUP_CONCAT(source_column || '->' || target_column)
                            FROM column_lineage cl
                            WHERE cl.lineage_id = l.lineage_id) as column_mappings
                    FROM lineage l
                    WHERE l.source_dataset_id = ?
                """, (current_id,))

            for row in cursor.fetchall():
                next_id = row['source_dataset_id'] if direction == 'upstream' else row['target_dataset_id']

                edges.append(LineageEdge(
                    source_id=row['source_dataset_id'],
                    target_id=row['target_dataset_id'],
                    lineage_type=row['lineage_type'],
                    transformation_code=row['transformation_code'],
                    column_mappings=self._parse_column_mappings(row['column_mappings'])
                ))

                traverse(next_id, depth + 1, distance + 1)

        traverse(dataset_id, 0, 0)

        return {
            'root_dataset': dataset_id,
            'direction': direction,
            'nodes': [
                {
                    'id': n.dataset_id,
                    'name': n.dataset_name,
                    'quality': n.quality_score,
                    'status': n.status,
                    'depth': n.depth,
                    'distance': n.distance
                }
                for n in nodes.values()
            ],
            'edges': [
                {
                    'source': e.source_id,
                    'target': e.target_id,
                    'type': e.lineage_type,
                    'columns': len(e.column_mappings)
                }
                for e in edges
            ],
            'node_count': len(nodes),
            'edge_count': len(edges),
            'max_depth': max(n.depth for n in nodes.values()) if nodes else 0
        }

    def analyze_impact(
        self,
        dataset_id: str,
        scope: ImpactScope = ImpactScope.DOWNSTREAM,
        max_depth: int = 10
    ) -> ImpactAnalysis:
        """
        Analyze impact of changes to a dataset

        Args:
            dataset_id: Dataset to analyze
            scope: Scope of analysis
            max_depth: Maximum depth to traverse

        Returns:
            Impact analysis
        """
        if scope == ImpactScope.UPSTREAM:
            lineage = self.get_upstream_lineage(dataset_id, max_depth)
        elif scope == ImpactScope.DOWNSTREAM:
            lineage = self.get_downstream_lineage(dataset_id, max_depth)
        elif scope == ImpactScope.IMMEDIATE:
            lineage = self.get_downstream_lineage(dataset_id, max_depth=1)
        else:  # FULL
            upstream = self.get_upstream_lineage(dataset_id, max_depth)
            downstream = self.get_downstream_lineage(dataset_id, max_depth)
            lineage = {
                'nodes': upstream['nodes'] + downstream['nodes'],
                'edges': upstream['edges'] + downstream['edges'],
                'max_depth': max(upstream.get('max_depth', 0), downstream.get('max_depth', 0))
            }

        # Extract affected datasets (excluding root)
        affected = [n['id'] for n in lineage['nodes'] if n['id'] != dataset_id]

        # Calculate risk score based on:
        # - Number of affected datasets
        # - Quality scores
        # - Depth of impact
        risk_score = self._calculate_risk_score(lineage)

        # Find critical path (longest dependency chain)
        critical_path = self._find_critical_path(dataset_id, lineage)

        # Generate recommendations
        recommendations = self._generate_impact_recommendations(
            len(affected),
            risk_score,
            lineage.get('max_depth', 0)
        )

        return ImpactAnalysis(
            affected_datasets=affected,
            affected_count=len(affected),
            critical_path=critical_path,
            risk_score=risk_score,
            max_depth=lineage.get('max_depth', 0),
            recommendations=recommendations
        )

    def _calculate_risk_score(self, lineage: Dict) -> float:
        """
        Calculate risk score based on impact

        Returns score between 0 and 1
        """
        node_count = len(lineage['nodes'])
        max_depth = lineage.get('max_depth', 0)

        # Base risk on number of affected datasets
        count_score = min(node_count / 20.0, 1.0)  # Cap at 20 datasets

        # Factor in depth (deeper = higher risk)
        depth_score = min(max_depth / 10.0, 1.0)  # Cap at depth 10

        # Average quality of affected datasets
        avg_quality = sum(n.get('quality', 0) for n in lineage['nodes']) / max(node_count, 1)
        quality_factor = 1.0 - avg_quality  # Lower quality = higher risk

        # Combined risk score
        risk = (count_score * 0.4) + (depth_score * 0.3) + (quality_factor * 0.3)

        return round(risk, 3)

    def _find_critical_path(self, root_id: str, lineage: Dict) -> List[str]:
        """Find longest dependency path (critical path)"""
        # Build adjacency list
        adj = {}
        for edge in lineage['edges']:
            source = edge['source']
            target = edge['target']
            if source not in adj:
                adj[source] = []
            adj[source].append(target)

        # DFS to find longest path
        longest_path = []

        def dfs(node: str, path: List[str]):
            nonlocal longest_path
            path.append(node)

            if len(path) > len(longest_path):
                longest_path = path.copy()

            if node in adj:
                for neighbor in adj[node]:
                    dfs(neighbor, path)

            path.pop()

        dfs(root_id, [])

        # Convert IDs to names
        id_to_name = {n['id']: n['name'] for n in lineage['nodes']}
        return [id_to_name.get(id, id) for id in longest_path]

    def _generate_impact_recommendations(
        self,
        affected_count: int,
        risk_score: float,
        max_depth: int
    ) -> List[str]:
        """Generate recommendations based on impact analysis"""
        recommendations = []

        if affected_count == 0:
            recommendations.append("No downstream dependencies - safe to modify")
            return recommendations

        if risk_score > 0.7:
            recommendations.append("HIGH RISK: Coordinate with all affected teams before changes")
            recommendations.append("Consider creating a new dataset version instead")
        elif risk_score > 0.4:
            recommendations.append("MEDIUM RISK: Review changes with downstream consumers")
            recommendations.append("Test changes in staging environment first")
        else:
            recommendations.append("LOW RISK: Monitor downstream datasets after changes")

        if affected_count > 10:
            recommendations.append(
                f"Large blast radius: {affected_count} datasets affected"
            )

        if max_depth > 5:
            recommendations.append(
                f"Deep dependency chain: {max_depth} levels - changes may cascade"
            )

        return recommendations

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies in lineage graph

        Returns:
            List of circular dependency chains
        """
        cursor = self.conn.cursor()

        # Build adjacency list
        cursor.execute("SELECT source_dataset_id, target_dataset_id FROM lineage")

        adj = {}
        for row in cursor.fetchall():
            source = row['source_dataset_id']
            target = row['target_dataset_id']
            if source not in adj:
                adj[source] = []
            adj[source].append(target)

        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in adj:
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        dfs(neighbor, path)
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        # Check all nodes
        for node in adj.keys():
            if node not in visited:
                dfs(node, [])

        return cycles

    def get_column_lineage(
        self,
        dataset_id: str,
        column_name: str,
        direction: str = 'both',
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Get column-level lineage

        Args:
            dataset_id: Dataset identifier
            column_name: Column name
            direction: 'upstream', 'downstream', or 'both'
            max_depth: Maximum traversal depth

        Returns:
            Column lineage graph
        """
        cursor = self.conn.cursor()

        nodes = []
        edges = []
        visited = set()

        def traverse(ds_id: str, col_name: str, depth: int, dir: str):
            if depth > max_depth:
                return

            key = f"{ds_id}:{col_name}"
            if key in visited:
                return

            visited.add(key)
            nodes.append({'dataset': ds_id, 'column': col_name, 'depth': depth})

            if dir in ['upstream', 'both']:
                # Get source columns
                cursor.execute("""
                    SELECT l.source_dataset_id, cl.source_column, cl.transformation
                    FROM column_lineage cl
                    JOIN lineage l ON cl.lineage_id = l.lineage_id
                    WHERE l.target_dataset_id = ? AND cl.target_column = ?
                """, (ds_id, col_name))

                for row in cursor.fetchall():
                    source_ds = row['source_dataset_id']
                    source_col = row['source_column']
                    transform = row['transformation']

                    edges.append({
                        'from': {'dataset': source_ds, 'column': source_col},
                        'to': {'dataset': ds_id, 'column': col_name},
                        'transformation': transform
                    })

                    traverse(source_ds, source_col, depth + 1, 'upstream')

            if dir in ['downstream', 'both']:
                # Get target columns
                cursor.execute("""
                    SELECT l.target_dataset_id, cl.target_column, cl.transformation
                    FROM column_lineage cl
                    JOIN lineage l ON cl.lineage_id = l.lineage_id
                    WHERE l.source_dataset_id = ? AND cl.source_column = ?
                """, (ds_id, col_name))

                for row in cursor.fetchall():
                    target_ds = row['target_dataset_id']
                    target_col = row['target_column']
                    transform = row['transformation']

                    edges.append({
                        'from': {'dataset': ds_id, 'column': col_name},
                        'to': {'dataset': target_ds, 'column': target_col},
                        'transformation': transform
                    })

                    traverse(target_ds, target_col, depth + 1, 'downstream')

        traverse(dataset_id, column_name, 0, direction)

        return {
            'root_column': {'dataset': dataset_id, 'column': column_name},
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }

    def get_data_freshness_path(self, dataset_id: str) -> Dict[str, Any]:
        """
        Analyze data freshness through lineage chain

        Args:
            dataset_id: Dataset identifier

        Returns:
            Freshness analysis
        """
        cursor = self.conn.cursor()

        # Get upstream lineage
        lineage = self.get_upstream_lineage(dataset_id, max_depth=10)

        # Get update times for all datasets
        freshness = []
        for node in lineage['nodes']:
            cursor.execute("""
                SELECT dataset_name, updated_at
                FROM datasets
                WHERE dataset_id = ?
            """, (node['id'],))

            row = cursor.fetchone()
            if row:
                freshness.append({
                    'dataset_id': node['id'],
                    'dataset_name': row['dataset_name'],
                    'updated_at': row['updated_at'],
                    'depth': node['depth']
                })

        # Sort by update time
        freshness.sort(key=lambda x: x['updated_at'])

        oldest = freshness[0] if freshness else None
        newest = freshness[-1] if freshness else None

        return {
            'dataset_id': dataset_id,
            'upstream_count': len(lineage['nodes']) - 1,
            'oldest_source': oldest,
            'newest_source': newest,
            'all_sources': freshness,
            'recommendation': self._get_freshness_recommendation(oldest, newest)
        }

    def _get_freshness_recommendation(
        self,
        oldest: Optional[Dict],
        newest: Optional[Dict]
    ) -> str:
        """Generate freshness recommendation"""
        if not oldest or not newest:
            return "No upstream sources found"

        from datetime import datetime, timedelta

        oldest_time = datetime.fromisoformat(oldest['updated_at'])
        now = datetime.now()
        age = now - oldest_time

        if age > timedelta(days=7):
            return f"WARNING: Oldest source ({oldest['dataset_name']}) is {age.days} days old"
        elif age > timedelta(days=1):
            return f"Oldest source is {age.days} days old - consider refreshing"
        else:
            return "Data sources are fresh"

    def _parse_column_mappings(self, mapping_str: Optional[str]) -> List[Tuple[str, str]]:
        """Parse column mapping string"""
        if not mapping_str:
            return []

        mappings = []
        for pair in mapping_str.split(','):
            if '->' in pair:
                source, target = pair.split('->')
                mappings.append((source.strip(), target.strip()))

        return mappings

    def export_lineage_graph(self, format: str = 'graphviz') -> str:
        """
        Export lineage graph in specified format

        Args:
            format: 'graphviz', 'mermaid', or 'json'

        Returns:
            Formatted graph string
        """
        graph = self.build_full_graph()

        if format == 'graphviz':
            return self._export_graphviz(graph)
        elif format == 'mermaid':
            return self._export_mermaid(graph)
        else:  # json
            import json
            return json.dumps(graph, indent=2)

    def _export_graphviz(self, graph: Dict) -> str:
        """Export as Graphviz DOT format"""
        lines = ['digraph lineage {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')

        for node in graph['nodes']:
            label = f"{node['name']}\\nQ: {node['quality']:.0%}"
            lines.append(f'  "{node["id"]}" [label="{label}"];')

        for edge in graph['edges']:
            lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [label="{edge["type"]}"];')

        lines.append('}')
        return '\n'.join(lines)

    def _export_mermaid(self, graph: Dict) -> str:
        """Export as Mermaid diagram format"""
        lines = ['graph LR']

        for node in graph['nodes']:
            node_id = node['id'].replace('-', '_')
            lines.append(f'  {node_id}["{node["name"]}"]')

        for edge in graph['edges']:
            source_id = edge['source'].replace('-', '_')
            target_id = edge['target'].replace('-', '_')
            lines.append(f'  {source_id} -->|{edge["type"]}| {target_id}')

        return '\n'.join(lines)
