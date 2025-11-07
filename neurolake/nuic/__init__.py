"""
NeuroLake Unified Intelligence Catalog (NUIC)

Complete catalog system with:
- Database-backed catalog engine
- Schema evolution tracking
- Graph-based lineage with impact analysis
- Column-level lineage
- Quality time series tracking
- Advanced query and discovery API
- Reusable business logic, pipeline patterns, and templates
"""

# Core NUIC Engine
from .catalog_engine import NUICEngine, DatasetStatus, LineageType

# Schema Evolution
from .schema_evolution import (
    SchemaEvolutionTracker,
    ChangeType,
    SeverityLevel,
    SchemaChange,
    SchemaVersion
)

# Lineage Graph
from .lineage_graph import (
    LineageGraph,
    ImpactScope,
    LineageNode,
    LineageEdge,
    ImpactAnalysis
)

# Catalog Query API
from .catalog_api import (
    CatalogQueryAPI,
    SearchFilter,
    SearchResult
)

# Legacy components (for backward compatibility)
from .catalog import NUICatalog
from .pipeline_registry import PipelineRegistry
from .pattern_library import PatternLibrary
from .template_manager import TemplateManager

__all__ = [
    # Core Engine
    'NUICEngine',
    'DatasetStatus',
    'LineageType',

    # Schema Evolution
    'SchemaEvolutionTracker',
    'ChangeType',
    'SeverityLevel',
    'SchemaChange',
    'SchemaVersion',

    # Lineage
    'LineageGraph',
    'ImpactScope',
    'LineageNode',
    'LineageEdge',
    'ImpactAnalysis',

    # Query API
    'CatalogQueryAPI',
    'SearchFilter',
    'SearchResult',

    # Legacy
    'NUICatalog',
    'PipelineRegistry',
    'PatternLibrary',
    'TemplateManager',
]
