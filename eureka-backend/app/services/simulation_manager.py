from app.services.physics_engine import PhysicsEngine, ParticleType
from app.services.chemistry_engine import ChemistryEngine
from app.database import db
from typing import Dict, Any, List, Tuple
import logging
import uuid
import json

logger = logging.getLogger(__name__)

class SimulationManager:
    """Manages simulations combining physics and chemistry"""
    
    def __init__(self):
        self.simulations: Dict[str, Dict] = {}
        self.physics_engines: Dict[str, PhysicsEngine] = {}
        self.chemistry_engine = ChemistryEngine()
    
    async def create_simulation(
        self, 
        experiment_id: str,
        name: str,
        description: str,
        simulation_type: str = "molecular"
    ) -> str:
        """Create new simulation and store in memory/database"""
        
        sim_id = str(uuid.uuid4())
        
        self.simulations[sim_id] = {
            "id": sim_id,
            "experiment_id": experiment_id,
            "name": name,
            "description": description,
            "type": simulation_type,
            "status": "created",
            "particles": [],
            "reactions": [],
            "results": None,
            "created_at": None
        }
        self.physics_engines[sim_id] = PhysicsEngine()
        
        # Database persistence
        await db.execute("""
            INSERT INTO simulations (id, experiment_id, name, description, type, status)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, sim_id, experiment_id, name, description, simulation_type, "created")
        
        logger.info(f"Created simulation: {sim_id}")
        return sim_id
    
    async def add_particle_to_simulation(
        self,
        sim_id: str,
        particle_type: str,
        position: Tuple[float, float, float],
        mass: float = 1.0,
        charge: float = 0.0
    ) -> bool:
        """Add particle to simulation and record to database"""
        
        if sim_id not in self.simulations:
            logger.error(f"Simulation not found: {sim_id}")
            return False
        
        particle_id = f"particle_{len(self.simulations[sim_id]['particles'])}"
        
        try:
            particle_type_enum = ParticleType[particle_type.upper()]
        except KeyError:
            logger.error(f"Invalid particle type: {particle_type}")
            return False
        
        engine = self.physics_engines.setdefault(sim_id, PhysicsEngine())
        engine.add_particle(
            particle_id=particle_id,
            particle_type=particle_type_enum,
            position=position,
            mass=mass,
            charge=charge
        )
        
        particle_data = {
            "id": particle_id,
            "type": particle_type,
            "position": position,
            "mass": mass,
            "charge": charge
        }
        self.simulations[sim_id]["particles"].append(particle_data)
        
        # Database persistence
        await db.execute("""
            INSERT INTO simulation_particles (simulation_id, particle_type, position, mass, charge)
            VALUES ($1, $2, $3, $4, $5)
        """, sim_id, particle_type, list(position), mass, charge)
        
        logger.info(f"Added particle {particle_id} to simulation {sim_id}")
        return True
    
    async def run_simulation(
        self,
        sim_id: str,
        steps: int = 1000,
        time_step: float = 0.001
    ) -> Dict[str, Any]:
        """Run simulation, save results to memory/database"""
        
        if sim_id not in self.simulations:
            return {"error": "Simulation not found"}
        
        self.simulations[sim_id]["status"] = "running"
        await db.execute("""
            UPDATE simulations SET status = $1 WHERE id = $2
        """, "running", sim_id)
        
        try:
            engine = self.physics_engines.setdefault(sim_id, PhysicsEngine())
            engine.time_step = time_step
            results = engine.run_simulation(steps)
            
            self.simulations[sim_id]["results"] = results
            self.simulations[sim_id]["status"] = "completed"
            
            # Database persistence
            await db.execute("""
                UPDATE simulations SET status = $1 WHERE id = $2
            """, "completed", sim_id)
            
            # Save results (JSON stringify trajectory)
            trajectory_json = json.dumps(results["trajectory"])
            await db.execute("""
                INSERT INTO simulation_results (simulation_id, trajectory, energies, final_energy, simulation_time)
                VALUES ($1, $2, $3, $4, $5)
            """, sim_id, trajectory_json, results["energies"], results["final_energy"], results["simulation_time"])
            
            logger.info(f"Simulation completed: {sim_id}")
            
            return {
                "status": "success",
                "simulation_id": sim_id,
                "results": results
            }
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            self.simulations[sim_id]["status"] = "failed"
            await db.execute("""
                UPDATE simulations SET status = $1 WHERE id = $2
            """, "failed", sim_id)
            return {"error": str(e)}
    
    async def add_reaction_to_simulation(
        self,
        sim_id: str,
        reactants: List[str],
        products: List[str],
        conditions: Dict[str, Any] = None
    ) -> bool:
        """Add chemical reaction to simulation and record to database"""
        
        if sim_id not in self.simulations:
            return False
        
        reaction_result = self.chemistry_engine.simulate_reaction(
            reactant_smiles=reactants,
            product_smiles=products,
            conditions=conditions or {}
        )
        
        if "error" in reaction_result:
            logger.error(f"Reaction simulation failed: {reaction_result['error']}")
            return False
            
        self.simulations[sim_id]["reactions"].append(reaction_result)
        
        # Database persistence
        await db.execute("""
            INSERT INTO simulation_reactions (simulation_id, reactants, products, energy_change, feasible)
            VALUES ($1, $2, $3, $4, $5)
        """, sim_id, reactants, products, reaction_result["energy_change"], reaction_result["feasible"])
        
        logger.info(f"Added reaction to simulation {sim_id}")
        return True
    
    def get_simulation_state(self, sim_id: str) -> Dict[str, Any]:
        """Get current simulation state"""
        
        if sim_id not in self.simulations:
            return {"error": "Simulation not found"}
        
        return {
            "simulation": self.simulations[sim_id],
            "physics_state": self.physics_engines.setdefault(sim_id, PhysicsEngine()).get_state()
        }
    
    def get_simulation_results(self, sim_id: str) -> Dict[str, Any]:
        """Get simulation results"""
        
        if sim_id not in self.simulations:
            return {"error": "Simulation not found"}
        
        sim = self.simulations[sim_id]
        
        return {
            "simulation_id": sim_id,
            "status": sim["status"],
            "results": sim["results"],
            "reactions": sim["reactions"]
        }
