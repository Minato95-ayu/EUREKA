from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.simulation_manager import SimulationManager
from typing import List, Dict, Any, Tuple

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
    particle_type: str
    position: List[float]
    mass: float = 1.0
    charge: float = 0.0

class AddReactionRequest(BaseModel):
    reactants: List[str]
    products: List[str]
    conditions: Dict[str, Any] = None

class RunSimulationRequest(BaseModel):
    steps: int = 1000
    time_step: float = 0.001

@router.post("/create")
async def create_simulation(req: CreateSimulationRequest):
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
async def add_particle(sim_id: str, req: AddParticleRequest):
    """Add particle to simulation"""
    try:
        if len(req.position) != 3:
            raise HTTPException(status_code=400, detail="Position must be a 3D coordinate [x, y, z]")
            
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
async def add_reaction(sim_id: str, req: AddReactionRequest):
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
async def run_simulation(sim_id: str, req: RunSimulationRequest = RunSimulationRequest()):
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
async def get_simulation_state(sim_id: str):
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
async def get_simulation_results(sim_id: str):
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
async def list_simulations():
    """List all simulations"""
    return {
        "simulations": list(sim_manager.simulations.values())
    }
