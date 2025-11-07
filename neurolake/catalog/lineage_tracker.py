"""
Lineage Tracker - Automatically track data lineage across the platform
"""

import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class LineageTracker:
    """
    Automatic data lineage tracking

    Tracks:
    - Query-level lineage (SELECT from table A -> View B)
    - Pipeline-level lineage (Pipeline reads from A, B -> writes to C)
    - Transformation lineage (Transformation T uses column X -> produces column Y)
    - File-level lineage (File A processed -> File B created)
    """

    def __init__(self, storage_path: str = "./lineage_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.lineage_graph: Dict[str, Dict] = {}  # asset_id -> lineage record
        self.column_lineage: Dict[str, List[str]] = {}  # column -> source columns

        self._load_lineage()

    def _load_lineage(self):
        """Load lineage from storage"""
        lineage_file = self.storage_path / "lineage.json"
        if lineage_file.exists():
            try:
                with open(lineage_file, 'r') as f:
                    data = json.load(f)
                    self.lineage_graph = data.get('lineage_graph', {})
                    self.column_lineage = data.get('column_lineage', {})
                logger.info(f"Loaded {len(self.lineage_graph)} lineage records")
            except Exception as e:
                logger.error(f"Error loading lineage: {e}")

    def _save_lineage(self):
        """Save lineage to storage"""
        lineage_file = self.storage_path / "lineage.json"
        try:
            with open(lineage_file, 'w') as f:
                json.dump({
                    'lineage_graph': self.lineage_graph,
                    'column_lineage': self.column_lineage
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving lineage: {e}")

    def track_query_lineage(
        self,
        query_id: str,
        input_tables: List[str],
        output_table: str,
        query_text: str = "",
        column_mapping: Dict[str, List[str]] = None
    ):
        """
        Track lineage for a query execution

        Args:
            query_id: Unique query identifier
            input_tables: List of input table IDs
            output_table: Output table ID
            query_text: SQL query text
            column_mapping: {output_column: [source_columns]}
        """
        self.lineage_graph[query_id] = {
            'type': 'query',
            'query_id': query_id,
            'inputs': input_tables,
            'outputs': [output_table],
            'query_text': query_text,
            'timestamp': datetime.utcnow().isoformat(),
            'column_mapping': column_mapping or {}
        }

        # Track column-level lineage
        if column_mapping:
            for output_col, source_cols in column_mapping.items():
                col_key = f"{output_table}.{output_col}"
                if col_key not in self.column_lineage:
                    self.column_lineage[col_key] = []
                self.column_lineage[col_key].extend(source_cols)
                self.column_lineage[col_key] = list(set(self.column_lineage[col_key]))  # Deduplicate

        self._save_lineage()
        logger.info(f"Tracked query lineage: {query_id}")

    def track_pipeline_lineage(
        self,
        pipeline_id: str,
        input_datasets: List[str],
        output_datasets: List[str],
        transformations: List[Dict] = None
    ):
        """Track lineage for a pipeline execution"""
        self.lineage_graph[pipeline_id] = {
            'type': 'pipeline',
            'pipeline_id': pipeline_id,
            'inputs': input_datasets,
            'outputs': output_datasets,
            'transformations': transformations or [],
            'timestamp': datetime.utcnow().isoformat()
        }

        self._save_lineage()
        logger.info(f"Tracked pipeline lineage: {pipeline_id}")

    def track_transformation(
        self,
        transformation_id: str,
        input_columns: List[str],
        output_columns: List[str],
        transformation_logic: str = ""
    ):
        """Track column-level transformation lineage"""
        self.lineage_graph[transformation_id] = {
            'type': 'transformation',
            'transformation_id': transformation_id,
            'input_columns': input_columns,
            'output_columns': output_columns,
            'logic': transformation_logic,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Update column lineage
        for output_col in output_columns:
            if output_col not in self.column_lineage:
                self.column_lineage[output_col] = []
            self.column_lineage[output_col].extend(input_columns)
            self.column_lineage[output_col] = list(set(self.column_lineage[output_col]))

        self._save_lineage()
        logger.info(f"Tracked transformation lineage: {transformation_id}")

    def get_upstream_lineage(self, asset_id: str, depth: int = 5) -> Dict:
        """
        Get upstream lineage (sources) for an asset

        Returns a tree of all upstream dependencies up to specified depth
        """
        visited = set()
        lineage_tree = self._get_upstream_recursive(asset_id, depth, visited)
        return lineage_tree

    def _get_upstream_recursive(self, asset_id: str, depth: int, visited: Set[str]) -> Dict:
        """Recursively build upstream lineage tree"""
        if depth == 0 or asset_id in visited:
            return {}

        visited.add(asset_id)
        upstream = {
            'asset_id': asset_id,
            'sources': []
        }

        # Find all lineage records where this asset is an output
        for lin_id, lin_data in self.lineage_graph.items():
            if asset_id in lin_data.get('outputs', []):
                source_info = {
                    'lineage_id': lin_id,
                    'type': lin_data.get('type'),
                    'inputs': lin_data.get('inputs', []),
                    'upstream': []
                }

                # Recursively get upstream for each input
                for input_asset in lin_data.get('inputs', []):
                    input_lineage = self._get_upstream_recursive(input_asset, depth - 1, visited)
                    if input_lineage:
                        source_info['upstream'].append(input_lineage)

                upstream['sources'].append(source_info)

        return upstream if upstream['sources'] else {}

    def get_downstream_lineage(self, asset_id: str, depth: int = 5) -> Dict:
        """
        Get downstream lineage (consumers) for an asset

        Returns a tree of all downstream dependencies
        """
        visited = set()
        lineage_tree = self._get_downstream_recursive(asset_id, depth, visited)
        return lineage_tree

    def _get_downstream_recursive(self, asset_id: str, depth: int, visited: Set[str]) -> Dict:
        """Recursively build downstream lineage tree"""
        if depth == 0 or asset_id in visited:
            return {}

        visited.add(asset_id)
        downstream = {
            'asset_id': asset_id,
            'consumers': []
        }

        # Find all lineage records where this asset is an input
        for lin_id, lin_data in self.lineage_graph.items():
            if asset_id in lin_data.get('inputs', []):
                consumer_info = {
                    'lineage_id': lin_id,
                    'type': lin_data.get('type'),
                    'outputs': lin_data.get('outputs', []),
                    'downstream': []
                }

                # Recursively get downstream for each output
                for output_asset in lin_data.get('outputs', []):
                    output_lineage = self._get_downstream_recursive(output_asset, depth - 1, visited)
                    if output_lineage:
                        consumer_info['downstream'].append(output_lineage)

                downstream['consumers'].append(consumer_info)

        return downstream if downstream['consumers'] else {}

    def get_column_lineage(self, column_id: str) -> List[str]:
        """Get source columns for a given column"""
        return self.column_lineage.get(column_id, [])

    def get_impact_analysis(self, asset_id: str) -> Dict:
        """
        Perform impact analysis for an asset

        Returns all downstream assets that would be affected by changes
        """
        downstream = self.get_downstream_lineage(asset_id, depth=10)

        impact = {
            'asset_id': asset_id,
            'affected_assets': set(),
            'affected_by_type': {}
        }

        def collect_impacts(node):
            for consumer in node.get('consumers', []):
                for output in consumer.get('outputs', []):
                    impact['affected_assets'].add(output)

                    # Count by lineage type
                    lin_type = consumer.get('type', 'unknown')
                    impact['affected_by_type'][lin_type] = impact['affected_by_type'].get(lin_type, 0) + 1

                for down in consumer.get('downstream', []):
                    collect_impacts(down)

        collect_impacts(downstream)

        impact['affected_assets'] = list(impact['affected_assets'])
        impact['total_affected'] = len(impact['affected_assets'])

        return impact
