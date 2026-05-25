from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from app.services.dependency_engine import DependencyEngine
from app.security import require_role

router = APIRouter(prefix="/api/experiments", tags=["experiments"])
dependency_engine = DependencyEngine()

class WhatIfRequest(BaseModel):
    objectId: str = Field(..., description="The unique ID of the object (e.g., 'car_engine')")
    componentId: str = Field(..., description="The ID of the component being modified (e.g., 'cooling_fan')")
    modification: Dict[str, Any] = Field(..., description="Modification description dict (e.g., {'type': 'remove'})")

class WhatIfResponse(BaseModel):
    summary: str = Field(..., description="Text summary of the overall cascading result")
    metrics: Dict[str, Any] = Field(..., description="Propagated physical metrics after simulation")
    warnings: List[str] = Field(..., description="Critical cautions or alerts triggered by the cascade")
    trace: List[str] = Field(..., description="Chronological causal step-by-step trace of how values changed")

@router.post("/what-if", response_model=WhatIfResponse)
async def what_if_experiment(req: WhatIfRequest, user: dict = Depends(require_role("editor"))):
    """
    Runs a What-If experiment to calculate cascading physical parameters of the object modifications.
    """
    try:
        result = dependency_engine.evaluate_modification(
            object_id=req.objectId,
            component_id=req.componentId,
            modification=req.modification
        )
        return WhatIfResponse(
            summary=result["summary"],
            metrics=result["metrics"],
            warnings=result["warnings"],
            trace=result["trace"]
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
