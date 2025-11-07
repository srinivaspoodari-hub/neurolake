"""Template Manager - Manage code and query templates"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages reusable code and query templates"""
    
    def __init__(self):
        self.templates: Dict[str, str] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default templates"""
        self.templates['etl_incremental'] = '''
-- Incremental ETL Template
MERGE INTO {target_table} AS target
USING {source_table} AS source
ON target.{key_column} = source.{key_column}
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHERE source.{timestamp_column} > (SELECT MAX({timestamp_column}) FROM {target_table})
        '''
        
        self.templates['data_quality_check'] = '''
-- Data Quality Check Template
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT {key_column}) as unique_keys,
    SUM(CASE WHEN {key_column} IS NULL THEN 1 ELSE 0 END) as null_keys,
    MIN({timestamp_column}) as min_date,
    MAX({timestamp_column}) as max_date
FROM {table_name}
        '''
    
    def get_template(self, name: str, **kwargs) -> Optional[str]:
        """Get a template and substitute variables"""
        template = self.templates.get(name)
        if template and kwargs:
            return template.format(**kwargs)
        return template
    
    def add_template(self, name: str, template: str):
        """Add a new template"""
        self.templates[name] = template
        logger.info(f"Added template: {name}")
    
    def list_templates(self) -> List[str]:
        """List all available templates"""
        return list(self.templates.keys())
