from fastapi import APIRouter, HTTPException, WebSocket, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
from sqlalchemy import text
from app.database import db

from app.services.collaboration_service import CollaborationService, CollaborationRole
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.websocket.collaboration import CollaborationManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["collaboration"])

collab_service = CollaborationService()
analytics_service = AnalyticsService()
export_service = ExportService()
collab_manager = CollaborationManager()

# ============ PYDANTIC REQUEST MODELS ============

class CreateCollaborationRequest(BaseModel):
    experiment_id: str
    owner_id: str
    title: str
    description: str = ""

class AddCollaboratorRequest(BaseModel):
    user_id: str
    role: str = "editor"

class AddCommentRequest(BaseModel):
    user_id: str
    text: str
    line_number: Optional[int] = None

class CompareExperimentsRequest(BaseModel):
    experiment_ids: List[str]

class DetectAnomaliesRequest(BaseModel):
    threshold: float = 2.0

# ============ COLLABORATION ENDPOINTS ============

@router.post("/collaborations/create")
async def create_collaboration(req: CreateCollaborationRequest):
    """Create collaboration"""
    try:
        collab_id = await collab_service.create_collaboration(
            experiment_id=req.experiment_id,
            owner_id=req.owner_id,
            title=req.title,
            description=req.description
        )
        return {"status": "success", "collaboration_id": collab_id}
    except Exception as e:
        logger.error(f"Create collaboration API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collaborations/{collab_id}/add-member")
async def add_collaborator(
    collab_id: str,
    req: AddCollaboratorRequest
):
    """Add collaborator"""
    try:
        success = await collab_service.add_collaborator(
            collab_id=collab_id,
            user_id=req.user_id,
            role=req.role
        )
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Add collaborator API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collaborations/{collab_id}/comment")
async def add_comment(
    collab_id: str,
    req: AddCommentRequest
):
    """Add comment"""
    try:
        comment = await collab_service.add_comment(
            collab_id=collab_id,
            user_id=req.user_id,
            text=req.text,
            line_number=req.line_number
        )
        # Broadcast the comment to active websocket sessions
        await collab_manager.broadcast_comment(collab_id, comment)
        return {"status": "success", "comment": comment}
    except Exception as e:
        logger.error(f"Add comment API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collaborations/{collab_id}")
async def get_collaboration(collab_id: str):
    """Get collaboration state"""
    try:
        state = await collab_service.get_collaboration_state(collab_id)
        if "error" in state:
            raise HTTPException(status_code=404, detail=state["error"])
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get collaboration API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ ANALYTICS ENDPOINTS ============

@router.post("/analytics/compare")
async def compare_experiments(req: CompareExperimentsRequest):
    """Compare experiments"""
    try:
        comparison = await analytics_service.compare_experiments(req.experiment_ids)
        return comparison
    except Exception as e:
        logger.error(f"Compare experiments API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analytics/{exp_id}/anomalies")
async def detect_anomalies(
    exp_id: str,
    req: DetectAnomaliesRequest
):
    """Detect anomalies"""
    try:
        anomalies = await analytics_service.detect_anomalies(exp_id, req.threshold)
        return {"anomalies": anomalies}
    except Exception as e:
        logger.error(f"Detect anomalies API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{exp_id}/trends")
async def analyze_trends(exp_id: str):
    """Analyze trends"""
    try:
        trends = await analytics_service.trend_analysis(exp_id)
        return trends
    except Exception as e:
        logger.error(f"Analyze trends API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ EXPORT ENDPOINTS ============

async def _fetch_experiment_data(exp_id: str) -> Dict[str, Any]:
    """Helper to fetch experiment & simulation results from DB or use mock fallback"""
    experiment = {
        "id": exp_id, 
        "name": f"Experiment {exp_id}", 
        "description": "Virtual Laboratory Experiment Output",
        "created_at": datetime.utcnow().isoformat(),
        "results": {}
    }
    
    if db.is_connected and db.engine:
        try:
            with db.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT name, description, created_at FROM simulations WHERE id = :id"), 
                    {"id": exp_id}
                ).fetchone()
                if row:
                    experiment["name"] = row[0]
                    experiment["description"] = row[1] or experiment["description"]
                    experiment["created_at"] = row[2].isoformat() if row[2] else experiment["created_at"]
                    
                # Query results/trajectory
                traj_rows = conn.execute(
                    text("SELECT step_number, energy, simulation_time, step_data FROM simulation_results WHERE simulation_id = :id ORDER BY step_number ASC"), 
                    {"id": exp_id}
                ).fetchall()
                if traj_rows:
                    trajectory = []
                    for r in traj_rows:
                        step_data = r[3] if isinstance(r[3], dict) else json.loads(r[3] or "{}")
                        trajectory.append({
                            "time": r[2],
                            "particles": step_data.get("particles", [])
                        })
                    experiment["results"] = {
                        "trajectory": trajectory,
                        "final_energy": float(traj_rows[-1][1]) if traj_rows else 0.0,
                        "simulation_time": float(traj_rows[-1][2]) if traj_rows else 0.0
                    }
        except Exception as e:
            logger.error(f"Error loading database simulation for export: {e}")
            
    return experiment

@router.get("/experiments/{exp_id}/export/json")
async def export_json(exp_id: str):
    """Export as JSON"""
    try:
        experiment = await _fetch_experiment_data(exp_id)
        json_data = await export_service.export_json(experiment)
        return {"data": json_data}
    except Exception as e:
        logger.error(f"Export JSON API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/{exp_id}/export/csv")
async def export_csv(exp_id: str):
    """Export as CSV"""
    try:
        experiment = await _fetch_experiment_data(exp_id)
        csv_data = await export_service.export_csv(experiment)
        return {"data": csv_data}
    except Exception as e:
        logger.error(f"Export CSV API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/experiments/{exp_id}/doi")
async def generate_doi(exp_id: str):
    """Generate DOI"""
    try:
        doi = await export_service.generate_doi(exp_id)
        return {"doi": doi}
    except Exception as e:
        logger.error(f"Generate DOI API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ WEBSOCKET COLLABORATION ============

@router.websocket("/ws/collaboration/{collab_id}")
async def websocket_collaboration(websocket: WebSocket, collab_id: str):
    """WebSocket for real-time collaboration"""
    await collab_manager.connect(websocket, collab_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "change":
                await collab_manager.broadcast_change(
                    collab_id,
                    data.get("data"),
                    data.get("user_id")
                )
            elif data.get("type") == "comment":
                await collab_manager.broadcast_comment(
                    collab_id,
                    data.get("comment")
                )
    except Exception as e:
        logger.error(f"Collaboration WebSocket error: {str(e)}")
    finally:
        await collab_manager.disconnect(websocket, collab_id)
