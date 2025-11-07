"""
NUIC Catalog - Central registry for reusable intelligence patterns
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class NUICatalog:
    """
    Neuro Unified Intelligence Catalog

    Manages reusable pipeline logic, business rules, and transformation patterns
    that can be applied across different data workflows.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize NUIC Catalog

        Args:
            storage_path: Path to store catalog metadata (defaults to ./nuic_catalog)
        """
        self.storage_path = Path(storage_path or "./nuic_catalog")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.pipelines: Dict[str, Dict] = {}
        self.patterns: Dict[str, Dict] = {}
        self.templates: Dict[str, Dict] = {}
        self.business_rules: Dict[str, Dict] = {}

        self._load_catalog()

    def _load_catalog(self):
        """Load catalog from persistent storage"""
        catalog_file = self.storage_path / "catalog.json"
        if catalog_file.exists():
            try:
                with open(catalog_file, 'r') as f:
                    data = json.load(f)
                    self.pipelines = data.get('pipelines', {})
                    self.patterns = data.get('patterns', {})
                    self.templates = data.get('templates', {})
                    self.business_rules = data.get('business_rules', {})
                logger.info(f"Loaded NUIC catalog with {len(self.pipelines)} pipelines")
            except Exception as e:
                logger.error(f"Error loading catalog: {e}")

    def _save_catalog(self):
        """Save catalog to persistent storage"""
        catalog_file = self.storage_path / "catalog.json"
        try:
            data = {
                'pipelines': self.pipelines,
                'patterns': self.patterns,
                'templates': self.templates,
                'business_rules': self.business_rules,
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(catalog_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("NUIC catalog saved successfully")
        except Exception as e:
            logger.error(f"Error saving catalog: {e}")

    def register_pipeline(
        self,
        name: str,
        description: str,
        logic: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Register a reusable pipeline pattern

        Args:
            name: Pipeline name (unique identifier)
            description: Human-readable description
            logic: Pipeline logic definition (SQL, transformations, etc.)
            tags: List of tags for categorization
            metadata: Additional metadata

        Returns:
            Pipeline ID
        """
        pipeline_id = f"pipeline_{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.pipelines[pipeline_id] = {
            'name': name,
            'description': description,
            'logic': logic,
            'tags': tags or [],
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'usage_count': 0,
            'version': '1.0.0'
        }

        self._save_catalog()
        logger.info(f"Registered pipeline: {name} ({pipeline_id})")

        return pipeline_id

    def register_pattern(
        self,
        name: str,
        pattern_type: str,
        definition: Dict[str, Any],
        applicability: List[str]
    ) -> str:
        """
        Register a reusable business logic pattern

        Args:
            name: Pattern name
            pattern_type: Type (e.g., 'aggregation', 'join', 'filtering')
            definition: Pattern definition
            applicability: List of use cases where pattern applies

        Returns:
            Pattern ID
        """
        pattern_id = f"pattern_{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.patterns[pattern_id] = {
            'name': name,
            'type': pattern_type,
            'definition': definition,
            'applicability': applicability,
            'created_at': datetime.utcnow().isoformat(),
            'usage_count': 0
        }

        self._save_catalog()
        logger.info(f"Registered pattern: {name} ({pattern_id})")

        return pattern_id

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        """Retrieve a pipeline by ID"""
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline:
            pipeline['usage_count'] += 1
            self._save_catalog()
        return pipeline

    def search_pipelines(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for pipelines by name, description, or tags

        Args:
            query: Search query string
            tags: Filter by tags

        Returns:
            List of matching pipelines
        """
        results = []

        for pipeline_id, pipeline in self.pipelines.items():
            match = True

            if query:
                query_lower = query.lower()
                match = (
                    query_lower in pipeline['name'].lower() or
                    query_lower in pipeline['description'].lower()
                )

            if tags and match:
                match = any(tag in pipeline['tags'] for tag in tags)

            if match:
                results.append({
                    'id': pipeline_id,
                    **pipeline
                })

        # Sort by usage count descending
        results.sort(key=lambda x: x['usage_count'], reverse=True)

        return results

    def get_popular_patterns(self, limit: int = 10) -> List[Dict]:
        """Get most frequently used patterns"""
        patterns_list = [
            {'id': pid, **pattern}
            for pid, pattern in self.patterns.items()
        ]

        patterns_list.sort(key=lambda x: x['usage_count'], reverse=True)

        return patterns_list[:limit]

    def export_catalog(self, export_path: str):
        """Export entire catalog to a file"""
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        catalog_data = {
            'pipelines': self.pipelines,
            'patterns': self.patterns,
            'templates': self.templates,
            'business_rules': self.business_rules,
            'exported_at': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }

        with open(export_file, 'w') as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(f"Catalog exported to {export_path}")

    def import_catalog(self, import_path: str, merge: bool = True):
        """Import catalog from a file"""
        import_file = Path(import_path)

        if not import_file.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")

        with open(import_file, 'r') as f:
            catalog_data = json.load(f)

        if merge:
            self.pipelines.update(catalog_data.get('pipelines', {}))
            self.patterns.update(catalog_data.get('patterns', {}))
            self.templates.update(catalog_data.get('templates', {}))
            self.business_rules.update(catalog_data.get('business_rules', {}))
        else:
            self.pipelines = catalog_data.get('pipelines', {})
            self.patterns = catalog_data.get('patterns', {})
            self.templates = catalog_data.get('templates', {})
            self.business_rules = catalog_data.get('business_rules', {})

        self._save_catalog()
        logger.info(f"Catalog imported from {import_path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        return {
            'total_pipelines': len(self.pipelines),
            'total_patterns': len(self.patterns),
            'total_templates': len(self.templates),
            'total_business_rules': len(self.business_rules),
            'most_used_pipeline': max(
                self.pipelines.items(),
                key=lambda x: x[1]['usage_count'],
                default=(None, {'name': 'N/A', 'usage_count': 0})
            )[1]['name'],
            'storage_path': str(self.storage_path)
        }
