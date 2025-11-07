"""
NeuroLake Notebook API Endpoints
FastAPI endpoints for notebook system integration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

from neurolake_notebook_system import (
    NeuroLakeNotebook,
    NotebookCell,
    CellExecutionEngine,
    BucketWriter,
    NCFWriter
)

from notebook_advanced_features import (
    CompliancePolicyEngine,
    GovernanceEngine,
    DataLineageTracker,
    QueryOptimizer,
    AICodeCompletion,
    NeuroBrainIntegration,
    DataQualityChecker,
    SchemaEvolutionEngine,
    DataEncryption
)

# Create router
router = APIRouter(prefix="/api/notebook", tags=["notebook"])

# Initialize services
compliance_engine = CompliancePolicyEngine()
governance_engine = GovernanceEngine()
lineage_tracker = DataLineageTracker()
query_optimizer = QueryOptimizer()
code_completion = AICodeCompletion()
neuro_brain = NeuroBrainIntegration()
quality_checker = DataQualityChecker()
schema_evolution = SchemaEvolutionEngine()
encryption_service = DataEncryption()

# In-memory notebook storage (would use DB in production)
active_notebooks = {}


# Request/Response Models
class CreateNotebookRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddCellRequest(BaseModel):
    language: str = 'python'
    code: str = ''
    position: Optional[int] = None


class ExecuteCellRequest(BaseModel):
    cell_id: str
    context: Optional[Dict[str, Any]] = None


class ComplianceCheckRequest(BaseModel):
    data: Any


class OptimizeQueryRequest(BaseModel):
    sql: str


class CodeCompletionRequest(BaseModel):
    partial_code: str
    language: str


class DataQualityRequest(BaseModel):
    data: List[Dict]


class AnalyzePatternRequest(BaseModel):
    data: List[Dict]


# Notebook Management Endpoints
@router.post("/create")
async def create_notebook(request: CreateNotebookRequest):
    """Create a new notebook"""
    try:
        notebook = NeuroLakeNotebook(name=request.name)
        if request.description:
            notebook.metadata['description'] = request.description

        active_notebooks[notebook.notebook_id] = notebook

        return {
            "status": "success",
            "notebook_id": notebook.notebook_id,
            "name": notebook.name,
            "created_at": notebook.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_notebooks():
    """List all active notebooks"""
    try:
        notebooks_list = []
        for nb_id, nb in active_notebooks.items():
            notebooks_list.append({
                "notebook_id": nb_id,
                "name": nb.name,
                "cell_count": len(nb.cells),
                "created_at": nb.created_at.isoformat(),
                "modified_at": nb.modified_at.isoformat()
            })

        # Also check saved notebooks
        notebooks_dir = Path("C:/NeuroLake/notebooks")
        if notebooks_dir.exists():
            for nb_file in notebooks_dir.glob("*.nlnb"):
                if nb_file.stem not in active_notebooks:
                    notebooks_list.append({
                        "notebook_id": nb_file.stem,
                        "name": nb_file.stem,
                        "file_path": str(nb_file),
                        "saved": True
                    })

        return {
            "status": "success",
            "count": len(notebooks_list),
            "notebooks": notebooks_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notebook_id}")
async def get_notebook(notebook_id: str):
    """Get notebook details"""
    try:
        if notebook_id in active_notebooks:
            nb = active_notebooks[notebook_id]
            return {
                "status": "success",
                "notebook": {
                    "notebook_id": nb.notebook_id,
                    "name": nb.name,
                    "version": nb.version,
                    "cells": [cell.to_dict() for cell in nb.cells],
                    "metadata": nb.metadata
                }
            }
        else:
            # Try to load from file
            nb_path = Path(f"C:/NeuroLake/notebooks/{notebook_id}.nlnb")
            if nb_path.exists():
                nb = NeuroLakeNotebook.load(str(nb_path))
                active_notebooks[notebook_id] = nb
                return {
                    "status": "success",
                    "notebook": {
                        "notebook_id": nb.notebook_id,
                        "name": nb.name,
                        "cells": [cell.to_dict() for cell in nb.cells]
                    }
                }

        raise HTTPException(status_code=404, detail="Notebook not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notebook_id}/cell")
async def add_cell(notebook_id: str, request: AddCellRequest):
    """Add a cell to notebook"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        nb = active_notebooks[notebook_id]
        cell_id = nb.add_cell(request.language, request.code, request.position)

        return {
            "status": "success",
            "cell_id": cell_id,
            "notebook_id": notebook_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notebook_id}/execute/{cell_id}")
async def execute_cell(notebook_id: str, cell_id: str, request: Optional[ExecuteCellRequest] = None):
    """Execute a specific cell"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        nb = active_notebooks[notebook_id]
        context = request.context if request else {}

        result = await nb.execute_cell(cell_id, context)

        return {
            "status": "success",
            "execution_result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notebook_id}/execute-all")
async def execute_all_cells(notebook_id: str):
    """Execute all cells in notebook"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        nb = active_notebooks[notebook_id]
        results = await nb.execute_all()

        return {
            "status": "success",
            "cell_count": len(results),
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notebook_id}/save")
async def save_notebook(notebook_id: str):
    """Save notebook to file"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        nb = active_notebooks[notebook_id]
        path = nb.save()

        return {
            "status": "success",
            "file_path": path,
            "notebook_id": notebook_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Compliance & Governance Endpoints
@router.post("/compliance/check")
async def check_compliance(request: ComplianceCheckRequest):
    """Check data compliance"""
    try:
        pii_result = compliance_engine.detect_pii(request.data)
        compliance_result = compliance_engine.check_compliance({
            "data": request.data
        })

        return {
            "status": "success",
            "pii_detection": pii_result,
            "compliance": compliance_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/governance/audit-log")
async def get_audit_log(user: Optional[str] = None, resource: Optional[str] = None):
    """Get audit log"""
    try:
        filters = {}
        if user:
            filters['user'] = user
        if resource:
            filters['resource'] = resource

        log = governance_engine.get_audit_log(filters)

        return {
            "status": "success",
            "count": len(log),
            "audit_log": log
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Intelligence Endpoints
@router.post("/optimize/query")
async def optimize_query(request: OptimizeQueryRequest):
    """Get query optimization suggestions"""
    try:
        result = query_optimizer.analyze_query(request.sql)

        return {
            "status": "success",
            "optimization": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/completion/suggest")
async def get_code_completion(request: CodeCompletionRequest):
    """Get code completion suggestions"""
    try:
        suggestions = code_completion.get_suggestions(
            request.partial_code,
            request.language
        )

        return {
            "status": "success",
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neuro-brain/analyze")
async def analyze_with_neuro_brain(request: AnalyzePatternRequest):
    """Analyze data patterns with Neuro Brain"""
    try:
        insights = neuro_brain.analyze_data_pattern(request.data)

        return {
            "status": "success",
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/check")
async def check_data_quality(request: DataQualityRequest):
    """Check data quality"""
    try:
        result = quality_checker.check_quality(request.data)

        return {
            "status": "success",
            "quality_check": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Lineage Tracking Endpoints
@router.get("/lineage/{entity_id}")
async def get_lineage(entity_id: str):
    """Get data lineage"""
    try:
        lineage = lineage_tracker.get_lineage(entity_id)

        return {
            "status": "success",
            "lineage": lineage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "neurolake_notebook",
        "active_notebooks": len(active_notebooks),
        "features_enabled": [
            "multi_language_cells",
            "nlp_queries",
            "auto_catalog",
            "compliance",
            "governance",
            "neuro_brain",
            "data_quality",
            "lineage_tracking",
            "query_optimization",
            "code_completion",
            "encryption",
            "versioning"
        ]
    }


@router.get("/stats")
async def get_stats():
    """Get notebook system statistics"""
    try:
        total_cells = sum(len(nb.cells) for nb in active_notebooks.values())
        total_executions = sum(
            sum(cell.execution_count for cell in nb.cells)
            for nb in active_notebooks.values()
        )

        return {
            "status": "success",
            "statistics": {
                "active_notebooks": len(active_notebooks),
                "total_cells": total_cells,
                "total_executions": total_executions,
                "supported_languages": CellExecutionEngine.SUPPORTED_LANGUAGES,
                "compliance_policies": len(compliance_engine.policies),
                "audit_log_entries": len(governance_engine.audit_log)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export Endpoints
@router.get("/{notebook_id}/export/jupyter")
async def export_to_jupyter(notebook_id: str):
    """Export notebook to Jupyter format (.ipynb)"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        from notebook_export import NotebookExporter

        nb = active_notebooks[notebook_id]
        notebook_dict = {
            "notebook_id": nb.notebook_id,
            "name": nb.name,
            "version": nb.version,
            "cells": [cell.to_dict() for cell in nb.cells]
        }

        jupyter_content = NotebookExporter.to_jupyter(notebook_dict)

        return {
            "status": "success",
            "format": "jupyter",
            "content": jupyter_content,
            "filename": f"{nb.name}.ipynb"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notebook_id}/export/html")
async def export_to_html(notebook_id: str):
    """Export notebook to HTML format"""
    try:
        if notebook_id not in active_notebooks:
            raise HTTPException(status_code=404, detail="Notebook not found")

        from notebook_export import NotebookExporter

        nb = active_notebooks[notebook_id]
        notebook_dict = {
            "notebook_id": nb.notebook_id,
            "name": nb.name,
            "version": nb.version,
            "cells": [cell.to_dict() for cell in nb.cells]
        }

        html_content = NotebookExporter.to_html(notebook_dict)

        return {
            "status": "success",
            "format": "html",
            "content": html_content,
            "filename": f"{nb.name}.html"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
