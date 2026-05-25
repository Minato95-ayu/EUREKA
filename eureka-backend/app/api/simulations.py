from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.simulation_manager import SimulationManager
from typing import List, Dict, Any, Tuple
from app.config import get_settings
from app.security import require_role

router = APIRouter(prefix="/api/simulations", tags=["simulations"])

# Global simulation manager
sim_manager = SimulationManager()

# Pydantic request models for JSON body validation
class CreateSimulationRequest(BaseModel):
    experiment_id: str
    name: str
    description: str
    simulation_type: str = "molecular"

class AddParticleRequest(BaseModel):
    particle_type: str = Field(max_length=32)
    position: List[float] = Field(min_length=3, max_length=3)
    mass: float = Field(default=1.0, gt=0, le=1_000_000)
    charge: float = Field(default=0.0, ge=-1_000_000, le=1_000_000)

class AddReactionRequest(BaseModel):
    reactants: List[str]
    products: List[str]
    conditions: Dict[str, Any] = None

class RunSimulationRequest(BaseModel):
    steps: int = Field(default=1000, ge=1, le=5000)
    time_step: float = Field(default=0.001, gt=0, le=0.05)

@router.post("/create")
async def create_simulation(req: CreateSimulationRequest, user: dict = Depends(require_role("editor"))):
    """Create new simulation"""
    try:
        sim_id = await sim_manager.create_simulation(
            experiment_id=req.experiment_id,
            name=req.name,
            description=req.description,
            simulation_type=req.simulation_type
        )
        
        return {
            "status": "success",
            "simulation_id": sim_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{sim_id}/add-particle")
async def add_particle(sim_id: str, req: AddParticleRequest, user: dict = Depends(require_role("editor"))):
    """Add particle to simulation"""
    try:
        settings = get_settings()
        state = sim_manager.get_simulation_state(sim_id)
        if "error" in state:
            raise HTTPException(status_code=404, detail=state["error"])
        if len(state["simulation"]["particles"]) >= settings.MAX_SIMULATION_PARTICLES:
            raise HTTPException(status_code=413, detail="Simulation particle limit exceeded")
            
        position_tuple = (req.position[0], req.position[1], req.position[2])
        
        success = await sim_manager.add_particle_to_simulation(
            sim_id=sim_id,
            particle_type=req.particle_type,
            position=position_tuple,
            mass=req.mass,
            charge=req.charge
        )
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add particle")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{sim_id}/add-reaction")
async def add_reaction(sim_id: str, req: AddReactionRequest, user: dict = Depends(require_role("editor"))):
    """Add reaction to simulation"""
    try:
        success = await sim_manager.add_reaction_to_simulation(
            sim_id=sim_id,
            reactants=req.reactants,
            products=req.products,
            conditions=req.conditions
        )
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add reaction")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{sim_id}/run")
async def run_simulation(
    sim_id: str,
    req: RunSimulationRequest = RunSimulationRequest(),
    user: dict = Depends(require_role("editor"))
):
    """Run simulation"""
    try:
        result = await sim_manager.run_simulation(
            sim_id=sim_id,
            steps=req.steps,
            time_step=req.time_step
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{sim_id}/state")
async def get_simulation_state(sim_id: str, user: dict = Depends(require_role("viewer"))):
    """Get simulation state"""
    try:
        state = sim_manager.get_simulation_state(sim_id)
        if "error" in state:
            raise HTTPException(status_code=404, detail=state["error"])
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{sim_id}/results")
async def get_simulation_results(sim_id: str, user: dict = Depends(require_role("viewer"))):
    """Get simulation results"""
    try:
        results = sim_manager.get_simulation_results(sim_id)
        if "error" in results:
            raise HTTPException(status_code=404, detail=results["error"])
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_simulations(user: dict = Depends(require_role("viewer"))):
    """List all simulations"""
    return {
        "simulations": list(sim_manager.simulations.values())
    }
