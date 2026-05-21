import numpy as np
from typing import Dict, List, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ParticleType(Enum):
    """Types of particles in simulation"""
    ATOM = "atom"
    ELECTRON = "electron"
    PHOTON = "photon"

@dataclass
class Vector3:
    """3D Vector"""
    x: float
    y: float
    z: float
    
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x/mag, self.y/mag, self.z/mag)

@dataclass
class Particle:
    """Represents a particle in simulation"""
    id: str
    type: ParticleType
    position: Vector3
    velocity: Vector3
    acceleration: Vector3
    mass: float
    charge: float = 0.0
    radius: float = 1.0
    
    def update_position(self, dt: float):
        """Update position using velocity"""
        self.position = self.position + self.velocity * dt
    
    def update_velocity(self, dt: float):
        """Update velocity using acceleration"""
        self.velocity = self.velocity + self.acceleration * dt

class PhysicsEngine:
    """Simulates physics of molecular systems"""
    
    # Physical constants
    COULOMB_CONSTANT = 8.99e9  # N⋅m²/C²
    BOLTZMANN_CONSTANT = 1.38e-23  # J/K
    GRAVITATIONAL_CONSTANT = 6.67e-11  # N⋅m²/kg²
    
    def __init__(self, time_step: float = 0.001):
        self.time_step = time_step
        self.particles: Dict[str, Particle] = {}
        self.forces: Dict[str, Vector3] = {}
        self.total_energy = 0.0
        self.temperature = 300.0  # Kelvin
        self.simulation_time = 0.0
    
    def add_particle(
        self, 
        particle_id: str, 
        particle_type: ParticleType,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float] = (0, 0, 0),
        mass: float = 1.0,
        charge: float = 0.0,
        radius: float = 1.0
    ):
        """Add particle to simulation"""
        particle = Particle(
            id=particle_id,
            type=particle_type,
            position=Vector3(*position),
            velocity=Vector3(*velocity),
            acceleration=Vector3(0, 0, 0),
            mass=mass,
            charge=charge,
            radius=radius
        )
        self.particles[particle_id] = particle
        self.forces[particle_id] = Vector3(0, 0, 0)
        logger.info(f"Added particle: {particle_id}")
    
    def calculate_coulomb_force(
        self, 
        particle1: Particle, 
        particle2: Particle
    ) -> Vector3:
        """Calculate Coulomb force on particle1 due to particle2"""
        if particle1.charge == 0 or particle2.charge == 0:
            return Vector3(0, 0, 0)
        
        # Distance vector from 1 to 2
        r_vec = Vector3(
            particle2.position.x - particle1.position.x,
            particle2.position.y - particle1.position.y,
            particle2.position.z - particle1.position.z
        )
        
        distance = r_vec.magnitude()
        if distance < 0.1:  # Prevent singularity
            distance = 0.1
        
        # Force magnitude
        force_magnitude = (
            self.COULOMB_CONSTANT * 
            abs(particle1.charge * particle2.charge) / 
            (distance ** 2)
        )
        
        # Force direction
        r_normalized = r_vec.normalize()
        
        # Repulsive if same charge (points in -r_normalized direction), attractive if opposite (points in +r_normalized)
        if (particle1.charge * particle2.charge) > 0:
            force = r_normalized * (-force_magnitude)
        else:
            force = r_normalized * force_magnitude
        
        return force
    
    def calculate_van_der_waals_force(
        self, 
        particle1: Particle, 
        particle2: Particle
    ) -> Vector3:
        """Calculate Van der Waals force (London dispersion) on particle1 due to particle2"""
        # Distance vector from 1 to 2
        r_vec = Vector3(
            particle2.position.x - particle1.position.x,
            particle2.position.y - particle1.position.y,
            particle2.position.z - particle1.position.z
        )
        
        distance = r_vec.magnitude()
        if distance < 0.1:
            distance = 0.1
        
        # Van der Waals force (simplified Lennard-Jones derivative)
        # F = -dU/dr where U = 4*epsilon * [(sigma/r)^12 - (sigma/r)^6]
        epsilon = 0.1  # Energy parameter
        sigma = 1.0    # Distance parameter
        
        force_magnitude = (
            24 * epsilon * (
                2 * (sigma**12 / distance**13) - 
                (sigma**6 / distance**7)
            )
        )
        
        r_normalized = r_vec.normalize()
        # dU/dr > 0 is repulsive, which should point in -r_normalized direction
        return r_normalized * (-force_magnitude)
    
    def calculate_all_forces(self):
        """Calculate forces on all particles"""
        # Reset forces
        for particle_id in self.forces:
            self.forces[particle_id] = Vector3(0, 0, 0)
        
        particle_list = list(self.particles.values())
        
        # Calculate pairwise forces
        for i, p1 in enumerate(particle_list):
            for p2 in particle_list[i+1:]:
                # Coulomb force
                coulomb = self.calculate_coulomb_force(p1, p2)
                
                # Van der Waals force
                vdw = self.calculate_van_der_waals_force(p1, p2)
                
                # Total force on p1 due to p2
                total_force = Vector3(
                    coulomb.x + vdw.x,
                    coulomb.y + vdw.y,
                    coulomb.z + vdw.z
                )
                
                # Apply Newton's third law: F12 = -F21
                self.forces[p1.id] = self.forces[p1.id] + total_force
                self.forces[p2.id] = self.forces[p2.id] + Vector3(
                    -total_force.x, -total_force.y, -total_force.z
                )
    
    def update_particles(self):
        """Update all particles (Verlet integration style updating)"""
        self.calculate_all_forces()
        
        for particle_id, particle in self.particles.items():
            # Calculate acceleration: F = ma -> a = F/m
            force = self.forces[particle_id]
            particle.acceleration = Vector3(
                force.x / particle.mass,
                force.y / particle.mass,
                force.z / particle.mass
            )
            
            # Update velocity and position
            particle.update_velocity(self.time_step)
            particle.update_position(self.time_step)
    
    def calculate_kinetic_energy(self) -> float:
        """Calculate total kinetic energy"""
        ke = 0.0
        for particle in self.particles.values():
            v_squared = (
                particle.velocity.x**2 + 
                particle.velocity.y**2 + 
                particle.velocity.z**2
            )
            ke += 0.5 * particle.mass * v_squared
        return ke
    
    def calculate_potential_energy(self) -> float:
        """Calculate total potential energy"""
        pe = 0.0
        particle_list = list(self.particles.values())
        
        for i, p1 in enumerate(particle_list):
            for p2 in particle_list[i+1:]:
                r_vec = Vector3(
                    p2.position.x - p1.position.x,
                    p2.position.y - p1.position.y,
                    p2.position.z - p1.position.z
                )
                distance = r_vec.magnitude()
                
                if distance > 0:
                    # Coulomb potential: U = k * q1 * q2 / r
                    if p1.charge != 0 and p2.charge != 0:
                        pe += (
                            self.COULOMB_CONSTANT * 
                            p1.charge * p2.charge / distance
                        )
                    
                    # Van der Waals potential: U = 4 * epsilon * [(sigma/r)^12 - (sigma/r)^6]
                    epsilon = 0.1
                    sigma = 1.0
                    pe += 4 * epsilon * (
                        (sigma/distance)**12 - (sigma/distance)**6
                    )
        
        return pe
    
    def step(self):
        """Execute one simulation step"""
        self.update_particles()
        self.simulation_time += self.time_step
        
        # Update total energy
        ke = self.calculate_kinetic_energy()
        pe = self.calculate_potential_energy()
        self.total_energy = ke + pe
    
    def run_simulation(self, steps: int) -> Dict[str, Any]:
        """Run simulation for N steps"""
        trajectory = []
        energies = []
        
        for _ in range(steps):
            self.step()
            
            # Record state
            state = {
                "time": self.simulation_time,
                "particles": [
                    {
                        "id": p.id,
                        "position": (p.position.x, p.position.y, p.position.z),
                        "velocity": (p.velocity.x, p.velocity.y, p.velocity.z)
                    }
                    for p in self.particles.values()
                ],
                "energy": self.total_energy
            }
            trajectory.append(state)
            energies.append(self.total_energy)
        
        return {
            "trajectory": trajectory,
            "energies": energies,
            "final_energy": self.total_energy,
            "simulation_time": self.simulation_time
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        return {
            "time": self.simulation_time,
            "particles": [
                {
                    "id": p.id,
                    "type": p.type.value,
                    "position": (p.position.x, p.position.y, p.position.z),
                    "velocity": (p.velocity.x, p.velocity.y, p.velocity.z),
                    "mass": p.mass,
                    "charge": p.charge
                }
                for p in self.particles.values()
            ],
            "kinetic_energy": self.calculate_kinetic_energy(),
            "potential_energy": self.calculate_potential_energy(),
            "total_energy": self.total_energy
        }
