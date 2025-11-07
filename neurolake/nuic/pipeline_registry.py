"""Pipeline Registry - Store and retrieve reusable pipeline patterns"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PipelineRegistry:
    """Manages registered pipeline patterns"""
    
    def __init__(self):
        self.pipelines: Dict[str, Dict] = {}
    
    def register(self, name: str, pipeline_def: Dict):
        """Register a pipeline pattern"""
        self.pipelines[name] = pipeline_def
        logger.info(f"Registered pipeline: {name}")
    
    def get(self, name: str) -> Optional[Dict]:
        """Retrieve a pipeline by name"""
        return self.pipelines.get(name)
    
    def list_all(self) -> List[str]:
        """List all registered pipelines"""
        return list(self.pipelines.keys())
