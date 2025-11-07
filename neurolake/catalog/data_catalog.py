"""
Comprehensive Data Catalog - Metadata about all data assets
Tracks tables, columns, files, datasets, schemas, and their relationships
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of data assets in the catalog"""
    TABLE = "table"
    VIEW = "view"
    FILE = "file"
    DATASET = "dataset"
    SCHEMA = "schema"
    COLUMN = "column"
    QUERY = "query"
    PIPELINE = "pipeline"
    TRANSFORMATION = "transformation"


class DataCatalog:
    """
    Comprehensive Data Catalog for NeuroLake

    Tracks metadata about all data assets:
    - Tables and views
    - Columns and data types
    - Files and datasets
    - Schemas and databases
    - Queries and transformations
    - Data lineage
    - Business glossary
    - Tags and classifications
    """

    def __init__(self, storage_path: str = "./catalog_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.assets: Dict[str, Dict] = {}
        self.tags: Dict[str, List[str]] = {}  # tag -> list of asset_ids
        self.lineage: Dict[str, Dict] = {}  # asset_id -> lineage info
        self.business_glossary: Dict[str, Dict] = {}

        self._load_catalog()

    def _load_catalog(self):
        """Load catalog from persistent storage"""
        catalog_file = self.storage_path / "catalog.json"
        if catalog_file.exists():
            try:
                with open(catalog_file, 'r') as f:
                    data = json.load(f)
                    self.assets = data.get('assets', {})
                    self.tags = data.get('tags', {})
                    self.lineage = data.get('lineage', {})
                    self.business_glossary = data.get('business_glossary', {})
                logger.info(f"Loaded catalog with {len(self.assets)} assets")
            except Exception as e:
                logger.error(f"Error loading catalog: {e}")

    def _save_catalog(self):
        """Save catalog to persistent storage"""
        catalog_file = self.storage_path / "catalog.json"
        try:
            with open(catalog_file, 'w') as f:
                json.dump({
                    'assets': self.assets,
                    'tags': self.tags,
                    'lineage': self.lineage,
                    'business_glossary': self.business_glossary
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")

    def register_table(
        self,
        table_name: str,
        database: str,
        schema: str,
        columns: List[Dict],
        description: str = "",
        owner: str = "",
        tags: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """
        Register a table in the catalog

        Args:
            table_name: Name of the table
            database: Database name
            schema: Schema name
            columns: List of column definitions [{"name": "id", "type": "int", "description": "..."}]
            description: Table description
            owner: Owner/team
            tags: Classification tags
            metadata: Additional metadata
        """
        asset_id = f"table_{database}_{schema}_{table_name}"

        self.assets[asset_id] = {
            'asset_id': asset_id,
            'asset_type': AssetType.TABLE.value,
            'name': table_name,
            'fully_qualified_name': f"{database}.{schema}.{table_name}",
            'database': database,
            'schema': schema,
            'description': description,
            'owner': owner,
            'columns': columns,
            'tags': tags or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'access_count': 0,
            'last_accessed': None
        }

        # Register columns
        for col in columns:
            col_asset_id = self.register_column(
                table_id=asset_id,
                column_name=col['name'],
                data_type=col.get('type', 'string'),
                description=col.get('description', ''),
                nullable=col.get('nullable', True),
                metadata=col.get('metadata', {})
            )

        # Update tags index
        for tag in (tags or []):
            if tag not in self.tags:
                self.tags[tag] = []
            if asset_id not in self.tags[tag]:
                self.tags[tag].append(asset_id)

        self._save_catalog()
        logger.info(f"Registered table: {asset_id}")
        return asset_id

    def register_column(
        self,
        table_id: str,
        column_name: str,
        data_type: str,
        description: str = "",
        nullable: bool = True,
        metadata: Dict = None
    ) -> str:
        """Register a column in the catalog"""
        asset_id = f"{table_id}_col_{column_name}"

        self.assets[asset_id] = {
            'asset_id': asset_id,
            'asset_type': AssetType.COLUMN.value,
            'name': column_name,
            'table_id': table_id,
            'data_type': data_type,
            'description': description,
            'nullable': nullable,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'sensitive': False,  # PII/sensitive data flag
            'business_term': None  # Link to business glossary
        }

        self._save_catalog()
        return asset_id

    def register_file(
        self,
        file_path: str,
        file_type: str,
        size_bytes: int,
        description: str = "",
        schema: Dict = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """Register a file/dataset in the catalog"""
        asset_id = f"file_{Path(file_path).stem}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.assets[asset_id] = {
            'asset_id': asset_id,
            'asset_type': AssetType.FILE.value,
            'name': Path(file_path).name,
            'file_path': file_path,
            'file_type': file_type,
            'size_bytes': size_bytes,
            'description': description,
            'schema': schema or {},
            'tags': tags or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        for tag in (tags or []):
            if tag not in self.tags:
                self.tags[tag] = []
            if asset_id not in self.tags[tag]:
                self.tags[tag].append(asset_id)

        self._save_catalog()
        logger.info(f"Registered file: {asset_id}")
        return asset_id

    def register_query(
        self,
        query_text: str,
        description: str = "",
        input_tables: List[str] = None,
        output_table: str = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """Register a query in the catalog and track lineage"""
        asset_id = f"query_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        self.assets[asset_id] = {
            'asset_id': asset_id,
            'asset_type': AssetType.QUERY.value,
            'query_text': query_text,
            'description': description,
            'input_tables': input_tables or [],
            'output_table': output_table,
            'tags': tags or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'execution_count': 0
        }

        # Track lineage
        if output_table and input_tables:
            self.lineage[asset_id] = {
                'type': 'query',
                'inputs': input_tables,
                'outputs': [output_table],
                'created_at': datetime.utcnow().isoformat()
            }

        self._save_catalog()
        logger.info(f"Registered query: {asset_id}")
        return asset_id

    def register_pipeline(
        self,
        pipeline_name: str,
        description: str,
        steps: List[Dict],
        input_datasets: List[str] = None,
        output_datasets: List[str] = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """Register a data pipeline in the catalog"""
        asset_id = f"pipeline_{pipeline_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.assets[asset_id] = {
            'asset_id': asset_id,
            'asset_type': AssetType.PIPELINE.value,
            'name': pipeline_name,
            'description': description,
            'steps': steps,
            'input_datasets': input_datasets or [],
            'output_datasets': output_datasets or [],
            'tags': tags or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'last_run': None,
            'run_count': 0,
            'status': 'active'
        }

        # Track lineage
        if input_datasets and output_datasets:
            self.lineage[asset_id] = {
                'type': 'pipeline',
                'inputs': input_datasets,
                'outputs': output_datasets,
                'steps': [s.get('name') for s in steps],
                'created_at': datetime.utcnow().isoformat()
            }

        for tag in (tags or []):
            if tag not in self.tags:
                self.tags[tag] = []
            if asset_id not in self.tags[tag]:
                self.tags[tag].append(asset_id)

        self._save_catalog()
        logger.info(f"Registered pipeline: {asset_id}")
        return asset_id

    def add_business_term(
        self,
        term: str,
        definition: str,
        related_columns: List[str] = None,
        synonyms: List[str] = None,
        metadata: Dict = None
    ):
        """Add a business glossary term"""
        self.business_glossary[term] = {
            'term': term,
            'definition': definition,
            'related_columns': related_columns or [],
            'synonyms': synonyms or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        self._save_catalog()

    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get asset metadata by ID"""
        asset = self.assets.get(asset_id)
        if asset:
            # Update access tracking
            asset['access_count'] = asset.get('access_count', 0) + 1
            asset['last_accessed'] = datetime.utcnow().isoformat()
            self._save_catalog()
        return asset

    def search_assets(
        self,
        query: str = None,
        asset_type: str = None,
        tags: List[str] = None,
        database: str = None,
        schema: str = None
    ) -> List[Dict]:
        """
        Search for assets in the catalog

        Args:
            query: Text search in name/description
            asset_type: Filter by asset type
            tags: Filter by tags
            database: Filter by database
            schema: Filter by schema
        """
        results = []

        for asset_id, asset in self.assets.items():
            # Filter by type
            if asset_type and asset['asset_type'] != asset_type:
                continue

            # Filter by database/schema
            if database and asset.get('database') != database:
                continue
            if schema and asset.get('schema') != schema:
                continue

            # Filter by tags
            if tags:
                asset_tags = asset.get('tags', [])
                if not any(tag in asset_tags for tag in tags):
                    continue

            # Text search
            if query:
                query_lower = query.lower()
                searchable = f"{asset.get('name', '')} {asset.get('description', '')} {asset.get('fully_qualified_name', '')}"
                if query_lower not in searchable.lower():
                    continue

            results.append(asset)

        # Sort by relevance (access count)
        results.sort(key=lambda x: x.get('access_count', 0), reverse=True)
        return results

    def get_lineage(self, asset_id: str, depth: int = 3) -> Dict:
        """
        Get data lineage for an asset

        Returns upstream and downstream dependencies
        """
        lineage_info = {
            'asset_id': asset_id,
            'upstream': [],
            'downstream': [],
            'depth': depth
        }

        # Find direct lineage
        if asset_id in self.lineage:
            lineage_info['direct'] = self.lineage[asset_id]

        # Find upstream (inputs)
        for lin_id, lin_data in self.lineage.items():
            if asset_id in lin_data.get('outputs', []):
                lineage_info['upstream'].append({
                    'lineage_id': lin_id,
                    'inputs': lin_data.get('inputs', []),
                    'type': lin_data.get('type')
                })

        # Find downstream (outputs)
        for lin_id, lin_data in self.lineage.items():
            if asset_id in lin_data.get('inputs', []):
                lineage_info['downstream'].append({
                    'lineage_id': lin_id,
                    'outputs': lin_data.get('outputs', []),
                    'type': lin_data.get('type')
                })

        return lineage_info

    def get_statistics(self) -> Dict:
        """Get catalog statistics"""
        stats = {
            'total_assets': len(self.assets),
            'by_type': {},
            'total_tags': len(self.tags),
            'total_lineage_entries': len(self.lineage),
            'total_business_terms': len(self.business_glossary)
        }

        # Count by type
        for asset in self.assets.values():
            asset_type = asset['asset_type']
            stats['by_type'][asset_type] = stats['by_type'].get(asset_type, 0) + 1

        return stats

    def get_popular_assets(self, limit: int = 10) -> List[Dict]:
        """Get most frequently accessed assets"""
        sorted_assets = sorted(
            self.assets.values(),
            key=lambda x: x.get('access_count', 0),
            reverse=True
        )
        return sorted_assets[:limit]

    def get_assets_by_tag(self, tag: str) -> List[Dict]:
        """Get all assets with a specific tag"""
        asset_ids = self.tags.get(tag, [])
        return [self.assets[aid] for aid in asset_ids if aid in self.assets]
