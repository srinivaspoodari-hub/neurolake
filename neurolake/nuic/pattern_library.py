"""Pattern Library - Common data transformation patterns"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PatternLibrary:
    """Library of reusable transformation patterns"""
    
    def __init__(self):
        self.patterns: Dict[str, Dict] = {}
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default transformation patterns"""
        self.patterns['scd_type2'] = {
            'name': 'Slowly Changing Dimension Type 2',
            'description': 'Track historical changes with effective dates',
            'sql_template': '''
                INSERT INTO {target_table}
                SELECT *, CURRENT_TIMESTAMP as effective_from, 
                       NULL as effective_to, TRUE as is_current
                FROM {source_table}
            '''
        }
        
        self.patterns['deduplication'] = {
            'name': 'Deduplication',
            'description': 'Remove duplicate records based on key',
            'sql_template': '''
                SELECT DISTINCT ON ({key_columns}) *
                FROM {source_table}
                ORDER BY {key_columns}, {timestamp_column} DESC
            '''
        }
    
    def get_pattern(self, name: str) -> Dict:
        """Get a pattern by name"""
        return self.patterns.get(name, {})
    
    def list_patterns(self) -> List[str]:
        """List all available patterns"""
        return list(self.patterns.keys())
