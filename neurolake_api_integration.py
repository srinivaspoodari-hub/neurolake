"""
NeuroLake API Integration
Complete REST API endpoints for NDM and NUIC functionality
Integrates: Ingestion, Catalog, Lineage, Schema Evolution, Quality Metrics
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import json
from datetime import datetime

# Import NeuroLake modules
from neurolake.ingestion import SmartIngestor, IngestionConfig
from neurolake.nuic import (
    NUICEngine,
    CatalogQueryAPI,
    LineageGraph,
    SchemaEvolutionTracker,
    ImpactScope,
    SearchFilter
)

# Create router
router = APIRouter(prefix="/api/neurolake", tags=["NeuroLake Platform"])

# Global instances (initialized on first use)
_nuic_engine = None
_catalog_api = None
_lineage_graph = None
_schema_tracker = None
_smart_ingestor = None

def get_nuic_engine():
    """Get or create NUIC engine instance"""
    global _nuic_engine
    if _nuic_engine is None:
        _nuic_engine = NUICEngine()
    return _nuic_engine

def get_catalog_api():
    """Get or create Catalog API instance"""
    global _catalog_api
    if _catalog_api is None:
        _catalog_api = CatalogQueryAPI(get_nuic_engine())
    return _catalog_api

def get_lineage_graph():
    """Get or create Lineage Graph instance"""
    global _lineage_graph
    if _lineage_graph is None:
        _lineage_graph = LineageGraph(get_nuic_engine())
    return _lineage_graph

def get_schema_tracker():
    """Get or create Schema Tracker instance"""
    global _schema_tracker
    if _schema_tracker is None:
        _schema_tracker = SchemaEvolutionTracker(get_nuic_engine())
    return _schema_tracker

def get_smart_ingestor():
    """Get or create Smart Ingestor instance"""
    global _smart_ingestor
    if _smart_ingestor is None:
        _smart_ingestor = SmartIngestor(nuic_engine=get_nuic_engine())
    return _smart_ingestor


# ============================================================================
# INGESTION ENDPOINTS
# ============================================================================

@router.post("/ingestion/upload")
async def upload_and_ingest(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    target_use_case: str = Form("analytics"),
    auto_execute_transformations: bool = Form(True),
    quality_threshold: float = Form(0.5)
):
    """
    Upload and ingest a data file

    Supports: CSV, JSON, Parquet, Excel
    """
    try:
        # Save uploaded file to temp location
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Use dataset name from form or derive from filename
        if not dataset_name:
            dataset_name = Path(file.filename).stem

        # Configure ingestion
        config_override = {
            'target_use_case': target_use_case,
            'auto_execute_transformations': auto_execute_transformations,
            'quality_threshold': quality_threshold
        }

        # Ingest
        ingestor = get_smart_ingestor()
        result = ingestor.ingest(
            source=tmp_path,
            dataset_name=dataset_name,
            config_override=config_override
        )

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        # Return result
        return {
            "success": result.success,
            "ingestion_id": result.ingestion_id,
            "dataset_name": result.dataset_name,
            "rows_ingested": result.rows_ingested,
            "quality_score": result.quality_assessment.overall_score if result.quality_assessment else 0,
            "routing_path": result.routing_path,
            "transformations_applied": result.transformations_applied,
            "catalog_entry_created": result.catalog_entry_created,
            "lineage_tracked": result.lineage_tracked,
            "ingestion_time_seconds": result.ingestion_time_seconds,
            "storage_location": result.storage_location,
            "warnings": result.warnings,
            "errors": result.errors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/ingestion/statistics")
async def get_ingestion_statistics():
    """Get ingestion statistics"""
    try:
        ingestor = get_smart_ingestor()
        stats = ingestor.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CATALOG ENDPOINTS
# ============================================================================

@router.get("/catalog/search")
async def search_catalog(
    query: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated
    min_quality: Optional[float] = None,
    max_quality: Optional[float] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Search datasets in catalog

    Query Parameters:
    - query: Text search across dataset names
    - tags: Comma-separated list of tags
    - min_quality: Minimum quality score (0-1)
    - max_quality: Maximum quality score (0-1)
    - status: Dataset status filter
    - limit: Max results
    - offset: Pagination offset
    """
    try:
        api = get_catalog_api()

        # Parse tags
        tag_list = tags.split(',') if tags else None

        # Quality range
        quality_range = None
        if min_quality is not None or max_quality is not None:
            quality_range = (min_quality or 0, max_quality or 1)

        # Search
        results = api.search(
            query=query,
            tags=tag_list,
            quality_range=quality_range,
            status=status,
            limit=limit,
            offset=offset
        )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/dataset/{dataset_id}")
async def get_dataset_details(dataset_id: str):
    """Get detailed information about a dataset"""
    try:
        nuic = get_nuic_engine()
        dataset = nuic.get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

        return dataset

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/insights/{dataset_id}")
async def get_dataset_insights(dataset_id: str):
    """Get comprehensive insights about a dataset"""
    try:
        api = get_catalog_api()
        insights = api.get_dataset_insights(dataset_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/recommendations/{dataset_id}")
async def get_dataset_recommendations(dataset_id: str, limit: int = 5):
    """Get recommended similar datasets"""
    try:
        api = get_catalog_api()
        recommendations = api.recommend_datasets(dataset_id, limit=limit)
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/popular")
async def get_popular_datasets(period_days: int = 30, limit: int = 10):
    """Get most popular datasets"""
    try:
        api = get_catalog_api()
        popular = api.get_popular_datasets(period_days=period_days, limit=limit)
        return {"datasets": popular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/quality-leaders")
async def get_quality_leaders(limit: int = 10):
    """Get highest quality datasets"""
    try:
        api = get_catalog_api()
        leaders = api.get_quality_leaders(limit=limit)
        return {"datasets": leaders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/statistics")
async def get_catalog_statistics():
    """Get catalog statistics"""
    try:
        api = get_catalog_api()
        stats = api.get_catalog_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/search-by-column")
async def search_by_column(
    column_name: str,
    data_type: Optional[str] = None,
    pii_type: Optional[str] = None,
    limit: int = 50
):
    """Search datasets by column characteristics"""
    try:
        api = get_catalog_api()
        results = api.search_by_column(
            column_name=column_name,
            data_type=data_type,
            pii_type=pii_type,
            limit=limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LINEAGE ENDPOINTS
# ============================================================================

@router.get("/lineage/downstream/{dataset_id}")
async def get_downstream_lineage(dataset_id: str, max_depth: int = 3):
    """Get downstream lineage (consumers)"""
    try:
        lineage = get_lineage_graph()
        graph = lineage.get_downstream_lineage(dataset_id, max_depth=max_depth)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/upstream/{dataset_id}")
async def get_upstream_lineage(dataset_id: str, max_depth: int = 3):
    """Get upstream lineage (sources)"""
    try:
        lineage = get_lineage_graph()
        graph = lineage.get_upstream_lineage(dataset_id, max_depth=max_depth)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/full-graph")
async def get_full_lineage_graph():
    """Get complete lineage graph for all datasets"""
    try:
        lineage = get_lineage_graph()
        graph = lineage.build_full_graph()
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/impact/{dataset_id}")
async def analyze_impact(
    dataset_id: str,
    scope: str = "downstream",  # downstream, upstream, full, immediate
    max_depth: int = 10
):
    """Analyze impact of changes to a dataset"""
    try:
        lineage = get_lineage_graph()

        # Map scope string to enum
        scope_map = {
            "downstream": ImpactScope.DOWNSTREAM,
            "upstream": ImpactScope.UPSTREAM,
            "full": ImpactScope.FULL,
            "immediate": ImpactScope.IMMEDIATE
        }

        scope_enum = scope_map.get(scope, ImpactScope.DOWNSTREAM)

        impact = lineage.analyze_impact(dataset_id, scope=scope_enum, max_depth=max_depth)

        return {
            "affected_datasets": impact.affected_datasets,
            "affected_count": impact.affected_count,
            "critical_path": impact.critical_path,
            "risk_score": impact.risk_score,
            "max_depth": impact.max_depth,
            "recommendations": impact.recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/column/{dataset_id}/{column_name}")
async def get_column_lineage(
    dataset_id: str,
    column_name: str,
    direction: str = "both",  # both, upstream, downstream
    max_depth: int = 5
):
    """Get column-level lineage"""
    try:
        lineage = get_lineage_graph()
        graph = lineage.get_column_lineage(
            dataset_id=dataset_id,
            column_name=column_name,
            direction=direction,
            max_depth=max_depth
        )
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/freshness/{dataset_id}")
async def get_data_freshness(dataset_id: str):
    """Analyze data freshness through lineage chain"""
    try:
        lineage = get_lineage_graph()
        freshness = lineage.get_data_freshness_path(dataset_id)
        return freshness
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/circular-dependencies")
async def detect_circular_dependencies():
    """Detect circular dependencies in lineage"""
    try:
        lineage = get_lineage_graph()
        cycles = lineage.detect_circular_dependencies()
        return {"cycles": cycles, "count": len(cycles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/export/{dataset_id}")
async def export_lineage_graph(
    dataset_id: str,
    format: str = "json",  # json, graphviz, mermaid
    max_depth: int = 3
):
    """Export lineage graph in various formats"""
    try:
        lineage = get_lineage_graph()

        # Get the graph
        graph_data = lineage.get_downstream_lineage(dataset_id, max_depth=max_depth)

        if format == "graphviz":
            # Export as Graphviz DOT
            content = lineage._export_graphviz(graph_data)
            return {"format": "graphviz", "content": content}
        elif format == "mermaid":
            # Export as Mermaid diagram
            content = lineage._export_mermaid(graph_data)
            return {"format": "mermaid", "content": content}
        else:
            # Return JSON
            return {"format": "json", "data": graph_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SCHEMA EVOLUTION ENDPOINTS
# ============================================================================

@router.get("/schema/history/{dataset_id}")
async def get_schema_history(dataset_id: str):
    """Get complete schema history for a dataset"""
    try:
        tracker = get_schema_tracker()
        history = tracker.get_schema_history(dataset_id)

        return {
            "dataset_id": dataset_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "version_number": v.version_number,
                    "columns": v.columns,
                    "changed_at": v.changed_at,
                    "changed_by": v.changed_by,
                    "change_description": v.change_description
                }
                for v in history
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/compare/{dataset_id}")
async def compare_schema_versions(dataset_id: str, version1: int, version2: int):
    """Compare two schema versions"""
    try:
        tracker = get_schema_tracker()
        changes = tracker.get_version_diff(dataset_id, version1, version2)

        return {
            "dataset_id": dataset_id,
            "version1": version1,
            "version2": version2,
            "changes": [
                {
                    "change_type": c.change_type.value,
                    "severity": c.severity.value,
                    "column_name": c.column_name,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "description": c.description,
                    "impact": c.impact
                }
                for c in changes
            ],
            "total_changes": len(changes),
            "breaking_changes": len([c for c in changes if c.severity.value == "breaking"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema/analyze-impact/{dataset_id}")
async def analyze_schema_impact(dataset_id: str, proposed_schema: List[Dict[str, Any]]):
    """Analyze impact of proposed schema changes"""
    try:
        tracker = get_schema_tracker()
        impact = tracker.analyze_impact(dataset_id, proposed_schema)
        return impact
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QUALITY METRICS ENDPOINTS
# ============================================================================

@router.get("/quality/time-series/{dataset_id}")
async def get_quality_time_series(
    dataset_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get quality metrics time series for a dataset"""
    try:
        nuic = get_nuic_engine()
        series = nuic.get_quality_time_series(
            dataset_id=dataset_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return {"dataset_id": dataset_id, "metrics": series}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/current/{dataset_id}")
async def get_current_quality(dataset_id: str):
    """Get current quality metrics for a dataset"""
    try:
        nuic = get_nuic_engine()
        dataset = nuic.get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Get latest quality metric
        series = nuic.get_quality_time_series(dataset_id, limit=1)
        latest_metric = series[0] if series else None

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.get('dataset_name'),
            "quality_score": dataset.get('quality_score'),
            "latest_measurement": latest_metric
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@router.get("/system/status")
async def get_system_status():
    """Get NeuroLake system status"""
    try:
        nuic = get_nuic_engine()
        catalog_stats = nuic.get_statistics()

        ingestor = get_smart_ingestor()
        ingestion_stats = ingestor.get_statistics()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "catalog": catalog_stats,
            "ingestion": ingestion_stats,
            "database": {
                "path": nuic.db_path,
                "connected": True
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/system/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "neurolake",
        "timestamp": datetime.now().isoformat()
    }
