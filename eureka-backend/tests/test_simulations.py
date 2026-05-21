import pytest
from unittest.mock import AsyncMock, patch
from app.services.physics_engine import Vector3, Particle, ParticleType, PhysicsEngine
from app.services.chemistry_engine import ChemistryEngine
from app.services.simulation_manager import SimulationManager

# ============ VECTOR3 TESTS ============

def test_vector3_operations():
    v1 = Vector3(1.0, 2.0, 3.0)
    v2 = Vector3(4.0, 5.0, 6.0)
    
    # Addition
    v3 = v1 + v2
    assert v3.x == 5.0
    assert v3.y == 7.0
    assert v3.z == 9.0
    
    # Scalar multiplication
    v4 = v1 * 2.0
    assert v4.x == 2.0
    assert v4.y == 4.0
    assert v4.z == 6.0
    
    # Magnitude
    mag = Vector3(3.0, 4.0, 0.0).magnitude()
    assert mag == 5.0
    
    # Normalization
    v5 = Vector3(3.0, 4.0, 0.0).normalize()
    assert v5.x == 0.6
    assert v5.y == 0.8
    assert v5.z == 0.0

# ============ PHYSICS ENGINE TESTS ============

def test_physics_engine_particle_addition():
    engine = PhysicsEngine()
    engine.add_particle(
        particle_id="p1",
        particle_type=ParticleType.ATOM,
        position=(0.0, 0.0, 0.0),
        velocity=(1.0, 0.0, 0.0),
        mass=12.0,
        charge=1.0,
        radius=1.5
    )
    
    assert "p1" in engine.particles
    p = engine.particles["p1"]
    assert p.type == ParticleType.ATOM
    assert p.position.x == 0.0
    assert p.velocity.x == 1.0
    assert p.mass == 12.0
    assert p.charge == 1.0
    assert p.radius == 1.5

def test_physics_coulomb_force():
    engine = PhysicsEngine()
    
    # Add two particles with opposite charges
    engine.add_particle("p1", ParticleType.ATOM, (0.0, 0.0, 0.0), charge=1.0)
    engine.add_particle("p2", ParticleType.ATOM, (1.0, 0.0, 0.0), charge=-1.0)
    
    p1 = engine.particles["p1"]
    p2 = engine.particles["p2"]
    
    # Opposite charges attract: force on p1 should point towards p2 (direction: +x)
    coulomb_force = engine.calculate_coulomb_force(p1, p2)
    assert coulomb_force.x > 0
    assert coulomb_force.y == 0
    assert coulomb_force.z == 0
    
    # Same charges repel: force on p1 should point away from p2 (direction: -x)
    p2.charge = 1.0
    coulomb_force = engine.calculate_coulomb_force(p1, p2)
    assert coulomb_force.x < 0
    assert coulomb_force.y == 0
    assert coulomb_force.z == 0

def test_physics_van_der_waals_force():
    engine = PhysicsEngine()
    
    # Place two neutral particles
    # LJ potential has minimum at distance = r_m = sigma * 2^(1/6) ~= 1.122
    # If distance < 1.122, it should be repulsive (pushed in -x direction)
    # If distance > 1.122, it should be attractive (pulled in +x direction)
    engine.add_particle("p1", ParticleType.ATOM, (0.0, 0.0, 0.0))
    engine.add_particle("p2", ParticleType.ATOM, (0.8, 0.0, 0.0)) # < 1.122
    
    p1 = engine.particles["p1"]
    p2 = engine.particles["p2"]
    
    vdw_force = engine.calculate_van_der_waals_force(p1, p2)
    assert vdw_force.x < 0  # Repulsive
    
    # Place p2 further away
    p2.position = Vector3(1.5, 0.0, 0.0) # > 1.122
    vdw_force = engine.calculate_van_der_waals_force(p1, p2)
    assert vdw_force.x > 0  # Attractive

def test_physics_energy_calculations():
    engine = PhysicsEngine()
    
    # Add moving particle for kinetic energy
    engine.add_particle("p1", ParticleType.ATOM, (0.0, 0.0, 0.0), velocity=(2.0, 0.0, 0.0), mass=2.0)
    ke = engine.calculate_kinetic_energy()
    assert ke == 0.5 * 2.0 * (2.0 ** 2)  # 4.0
    
    # Potential energy
    # Place two charged particles at distance = 2.0
    engine.add_particle("p2", ParticleType.ATOM, (2.0, 0.0, 0.0), charge=2.0)
    # Make p1 charged too
    engine.particles["p1"].charge = 1.0
    
    pe = engine.calculate_potential_energy()
    # pe should contain Coulomb potential + Lennard-Jones potential
    assert pe != 0.0

def test_physics_simulation_steps():
    engine = PhysicsEngine(time_step=0.01)
    engine.add_particle("p1", ParticleType.ATOM, (0.0, 0.0, 0.0), velocity=(1.0, 0.0, 0.0))
    engine.add_particle("p2", ParticleType.ATOM, (1.0, 0.0, 0.0))
    
    initial_x = engine.particles["p1"].position.x
    engine.step()
    final_x = engine.particles["p1"].position.x
    
    assert final_x != initial_x
    assert engine.simulation_time == 0.01

# ============ CHEMISTRY ENGINE TESTS ============

def test_chemistry_molecule_creation():
    chem = ChemistryEngine()
    
    # Ethanol SMILES
    success = chem.create_molecule_from_smiles("CCO", "ethanol")
    assert success is True
    assert "ethanol" in chem.molecules
    
    # Invalid SMILES
    success_invalid = chem.create_molecule_from_smiles("C=C=C=C=C=C=C=C=C=invalid", "invalid")
    assert success_invalid is False

def test_chemistry_molecule_properties():
    chem = ChemistryEngine()
    chem.create_molecule_from_smiles("CCO", "ethanol")
    
    props = chem.get_molecular_properties("ethanol")
    assert "molecular_weight" in props
    assert props["molecular_weight"] > 40.0
    assert props["formula"] == "C2H6O"
    assert props["num_atoms"] == 9  # C2H6O (2+6+1)
    assert props["num_bonds"] == 8

def test_chemistry_reaction_simulation():
    chem = ChemistryEngine()
    
    # Methane combustion: CH4 + 2 O2 -> CO2 + 2 H2O
    reactants = ["C", "O", "O"]
    products = ["C(=O)=O", "O", "O"]
    
    result = chem.simulate_reaction(reactants, products)
    assert "energy_change" in result
    assert "feasible" in result
    assert result["reactant_weight"] > 0
    assert result["product_weight"] > 0

def test_chemistry_reaction_rate():
    chem = ChemistryEngine()
    
    # predict rate at 300K
    rate = chem.predict_reaction_rate(activation_energy=50000, temperature=300)
    assert rate > 0
    assert rate < 1.0

# ============ SIMULATION MANAGER TESTS ============

@pytest.mark.asyncio
@patch("app.database.db.execute", new_callable=AsyncMock)
async def test_simulation_manager_flow(mock_db_execute):
    mgr = SimulationManager()
    
    # Create simulation
    sim_id = await mgr.create_simulation(
        experiment_id="exp_001",
        name="Water heating",
        description="Simulate heating"
    )
    assert sim_id is not None
    assert sim_id in mgr.simulations
    
    # Add particles
    p1_added = await mgr.add_particle_to_simulation(sim_id, "atom", (0.0, 0.0, 0.0), 16.0, -0.8)
    p2_added = await mgr.add_particle_to_simulation(sim_id, "electron", (1.0, 0.0, 0.0), 1.0, -1.0)
    assert p1_added is True
    assert p2_added is True
    
    # Add reaction
    rxn_added = await mgr.add_reaction_to_simulation(
        sim_id,
        reactants=["C"],
        products=["C(=O)=O"]
    )
    assert rxn_added is True
    
    # Run simulation
    run_result = await mgr.run_simulation(sim_id, steps=10, time_step=0.01)
    assert run_result["status"] == "success"
    assert "results" in run_result
    assert len(run_result["results"]["trajectory"]) == 10
    
    # Get state
    state = mgr.get_simulation_state(sim_id)
    assert "physics_state" in state
    assert len(state["physics_state"]["particles"]) == 2
    
    # Get results
    results = mgr.get_simulation_results(sim_id)
    assert results["status"] == "completed"
    assert len(results["reactions"]) == 1
