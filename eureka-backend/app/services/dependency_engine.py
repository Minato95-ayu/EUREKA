import json
import logging
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.services.object_repository import ObjectRepository
from app.services.object_library import ObjectLibrary

logger = logging.getLogger(__name__)

class DependencyEngine:
    """
    Evaluates cascading engineering effects and dependency propagation
    when object components are modified or removed.
    """

    def __init__(self, materials_path: Path | None = None, library_dir: Path | None = None):
        base_dir = Path(__file__).resolve().parents[1]
        self.materials_path = materials_path or base_dir / "data" / "materials" / "materials.json"
        self.library_dir = library_dir
        self.materials: Dict[str, Dict[str, Any]] = {}
        self.load_materials()

    def load_materials(self) -> None:
        """Loads physical constants for engineering materials."""
        try:
            if self.materials_path.exists():
                with open(self.materials_path, "r", encoding="utf-8") as f:
                    self.materials = json.load(f)
                logger.info(f"Loaded {len(self.materials)} materials from database.")
            else:
                logger.warning(f"Materials database not found at {self.materials_path}. Using fallback profiles.")
                self._set_fallback_materials()
        except Exception as e:
            logger.error(f"Error loading materials: {e}")
            self._set_fallback_materials()

    def _set_fallback_materials(self) -> None:
        self.materials = {
            "aluminum_alloy": {"name": "Aluminum Alloy", "density": 2.7, "thermal_limit": 300.0, "yield_strength": 276.0},
            "steel": {"name": "Forged Carbon Steel", "density": 7.85, "thermal_limit": 1200.0, "yield_strength": 415.0},
            "carbon_fiber": {"name": "Carbon Fiber", "density": 1.6, "thermal_limit": 400.0, "yield_strength": 900.0},
            "cast_iron": {"name": "Grey Cast Iron", "density": 7.2, "thermal_limit": 1150.0, "yield_strength": 240.0}
        }

    def _map_material_name(self, mat_name: str) -> str:
        """Maps a human-readable material string to a database key."""
        if not mat_name:
            return "steel"
        norm = mat_name.lower().replace(" ", "_").replace("-", "_")
        for key in self.materials.keys():
            if key in norm:
                return key
        if "aluminum" in norm:
            return "aluminum_alloy"
        if "iron" in norm:
            return "cast_iron"
        if "composite" in norm or "carbon" in norm:
            return "carbon_fiber"
        return "steel"

    def evaluate_modification(self, object_id: str, component_id: str, modification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates weight changes and propagates physical cascade effects down the component dependency tree.
        """
        # 1. Fetch Object Definition
        repo = ObjectRepository(library_dir=self.library_dir)
        obj = repo.load_object(object_id)
        if not obj:
            library = ObjectLibrary()
            obj = library.get_object(object_id)

        if not obj:
            raise ValueError(f"Object '{object_id}' not found in repository or library.")

        # Find target component
        target_component = next((c for c in obj.components if c.id == component_id), None)
        if not target_component:
            raise ValueError(f"Component '{component_id}' not found in object '{object_id}'.")

        # 2. Extract baseline characteristics with layout multipliers
        multipliers: Dict[str, float] = {}
        comp_by_id = {c.id: c for c in obj.components}
        
        def get_multiplier(comp_id: str) -> float:
            if comp_id in multipliers:
                return multipliers[comp_id]
            comp = comp_by_id.get(comp_id)
            if not comp:
                return 1.0
            local_mult = 1.0
            if comp.layout and isinstance(comp.layout, dict):
                layout_type = comp.layout.get("type")
                if layout_type in {"radial_array", "linear_array"}:
                    local_mult = float(comp.layout.get("count", 1.0))
                elif layout_type == "bilateral_mirror":
                    local_mult = 2.0
            parent_mult = 1.0
            if comp.parent_id:
                parent_mult = get_multiplier(comp.parent_id)
            multipliers[comp_id] = local_mult * parent_mult
            return multipliers[comp_id]

        total_weight_kg = 0.0
        component_masses: Dict[str, float] = {}
        for comp in obj.components:
            mass = 1.0
            if comp.simulation_properties and getattr(comp.simulation_properties, "mass", None) is not None:
                mass = float(comp.simulation_properties.mass)
            elif comp.geometry and "size" in comp.geometry:
                # Approximate volume for weight if mass missing
                size = comp.geometry["size"]
                if isinstance(size, list) and len(size) == 3:
                    vol = size[0] * size[1] * size[2]
                    mat_key = self._map_material_name(comp.material)
                    density = self.materials.get(mat_key, {}).get("density", 7.8)
                    mass = vol * density * 1000.0  # Scale mock unit
            
            # Apply layout repetition multiplier
            mult = get_multiplier(comp.id)
            effective_mass = mass * mult
            component_masses[comp.id] = effective_mass
            total_weight_kg += effective_mass

        trace: List[str] = []
        warnings: List[str] = []
        mod_type = modification.get("type", "remove")

        # 3. Handle modifications & run simulation cascade
        if "car_engine" in object_id:
            return self._run_engine_cascade(obj, target_component, mod_type, modification, component_masses, total_weight_kg, trace, warnings)
        elif "drone" in object_id or "quadcopter" in object_id:
            return self._run_drone_cascade(obj, target_component, mod_type, modification, component_masses, total_weight_kg, trace, warnings)
        else:
            # Generic fallback cascade
            return self._run_generic_cascade(obj, target_component, mod_type, modification, component_masses, total_weight_kg, trace, warnings)

    def _run_engine_cascade(
        self, obj: Any, target_comp: Any, mod_type: str, mod: Dict[str, Any],
        comp_masses: Dict[str, float], total_weight_kg: float, trace: List[str], warnings: List[str]
    ) -> Dict[str, Any]:
        """Engine cascading simulation."""
        
        # Baselines
        cooling_efficiency_pct = 100.0
        temperature_c = 85.0
        oil_viscosity_pct = 100.0
        friction_multiplier = 1.0
        mechanical_wear_rate = 1.0
        rpm_stability_pct = 100.0
        max_safe_rpm = 6000.0
        failure_risk_pct = 5.0

        # Apply weight modifications
        if mod_type == "remove":
            removed_mass = comp_masses.get(target_comp.id, 0.0)
            total_weight_kg = max(0.0, total_weight_kg - removed_mass)
            trace.append(f"Action: Removed '{target_comp.name}' component (reduced assembly weight by {removed_mass:.2f} kg)")
            
            # Causal link: if cooling fan is removed
            if "fan" in target_comp.id or "cooling" in target_comp.id:
                cooling_efficiency_pct = 20.0
                trace.append("Propagated: cooling_efficiency_pct decreased to 20.0% due to loss of forced air flow")
        
        elif mod_type == "change_material":
            new_mat_key = mod.get("value", "steel")
            old_mat_key = self._map_material_name(target_comp.material)
            
            if new_mat_key in self.materials and old_mat_key in self.materials:
                density_old = self.materials[old_mat_key]["density"]
                density_new = self.materials[new_mat_key]["density"]
                old_mass = comp_masses.get(target_comp.id, 0.0)
                new_mass = old_mass * (density_new / density_old)
                
                comp_masses[target_comp.id] = new_mass
                total_weight_kg = total_weight_kg - old_mass + new_mass
                trace.append(f"Action: Changed material of '{target_comp.name}' from {old_mat_key} to {new_mat_key}")
                trace.append(f"Propagated: weight of '{target_comp.name}' shifted from {old_mass:.2f} kg to {new_mass:.2f} kg")

                # Causal link: piston weight affects safe reciprocating RPM
                if "piston" in target_comp.id:
                    strength_old = self.materials[old_mat_key].get("yield_strength", 250.0)
                    strength_new = self.materials[new_mat_key].get("yield_strength", 250.0)
                    
                    # Safe speed scales with strength/density ratio
                    ratio = math.sqrt((strength_new / strength_old) * (density_old / density_new))
                    max_safe_rpm = int(6000.0 * ratio)
                    trace.append(f"Propagated: piston reciprocating mass changed, adjusting maximum safe threshold to {max_safe_rpm} RPM")

        # Run thermal/friction cascade calculations
        if cooling_efficiency_pct < 100.0:
            temperature_c = 85.0 + 0.8 * (100.0 - cooling_efficiency_pct)
            trace.append(f"Propagated: average operating temperature escalated to {temperature_c:.1f}°C")

        # Check material limits for pistons/blocks
        for comp_id, mass in comp_masses.items():
            comp = next((c for c in obj.components if c.id == comp_id), None)
            if not comp:
                continue
            mat_key = self._map_material_name(comp.material)
            if comp_id == target_comp.id and mod_type == "change_material":
                mat_key = mod.get("value", "steel")
            
            thermal_limit = self.materials.get(mat_key, {}).get("thermal_limit", 1000.0)
            if temperature_c > thermal_limit:
                failure_risk_pct = 100.0
                warnings.append(f"CRITICAL: Component '{comp.name}' temperature ({temperature_c:.1f}°C) exceeds material thermal limit of {thermal_limit}°C!")
                trace.append(f"Propagated: thermal breakdown in '{comp.name}' triggered complete system failure risk (100.0%)")

        if failure_risk_pct < 100.0:
            # Viscosity breakdown above 110C
            if temperature_c > 110.0:
                oil_viscosity_pct = max(5.0, 100.0 - 1.8 * (temperature_c - 110.0))
                trace.append(f"Propagated: oil viscosity degraded to {oil_viscosity_pct:.1f}% under extreme temperature")
                
                # Viscosity drop increases friction
                friction_multiplier = 1.0 + 4.5 * (1.0 - (oil_viscosity_pct / 100.0))
                trace.append(f"Propagated: mechanical boundary friction increased to {friction_multiplier:.2f}x")
                
                # Wear rate scales with friction
                mechanical_wear_rate = float(friction_multiplier ** 1.6)
                trace.append(f"Propagated: dynamic wear rate accelerated to {mechanical_wear_rate:.2f}x normal level")
                
                # Stability drops
                rpm_stability_pct = max(10.0, 100.0 - 18.0 * (friction_multiplier - 1.0))
                trace.append(f"Propagated: engine speed stability deteriorated to {rpm_stability_pct:.1f}% due to friction resistance")
                
                # Risk calculation
                failure_risk_pct = min(100.0, 5.0 + 12.0 * (mechanical_wear_rate - 1.0) + 0.6 * max(0.0, temperature_c - 120.0))
                trace.append(f"Propagated: cumulative engine failure risk evaluated at {failure_risk_pct:.1f}%")

        if failure_risk_pct > 80.0:
            warnings.append("WARNING: High risk of engine seizure or piston rod fracture due to severe lubrication loss!")
        elif failure_risk_pct > 30.0:
            warnings.append("CAUTION: Lubrication viscosity dropping. Long-term mechanical damage likely.")

        metrics = {
            "total_weight_kg": round(total_weight_kg, 2),
            "cooling_efficiency_pct": round(cooling_efficiency_pct, 1),
            "temperature_c": round(temperature_c, 1),
            "oil_viscosity_pct": round(oil_viscosity_pct, 1),
            "friction_multiplier": round(friction_multiplier, 2),
            "rpm_stability_pct": round(rpm_stability_pct, 1),
            "max_safe_rpm": max_safe_rpm,
            "failure_risk_pct": round(failure_risk_pct, 1)
        }

        summary = f"Modification of '{target_comp.name}' resulted in a weight of {total_weight_kg:.2f} kg and engine failure risk of {failure_risk_pct:.1f}%."
        return {
            "summary": summary,
            "metrics": metrics,
            "warnings": warnings,
            "trace": trace
        }

    def _run_drone_cascade(
        self, obj: Any, target_comp: Any, mod_type: str, mod: Dict[str, Any],
        comp_masses: Dict[str, float], total_weight_kg: float, trace: List[str], warnings: List[str]
    ) -> Dict[str, Any]:
        """Drone cascading simulation."""
        
        baseline_thrust = 3.6  # kg_f total thrust
        propeller_blades = 2
        power_consumption_multiplier = 1.0
        
        # Apply modifications
        if mod_type == "remove":
            removed_mass = comp_masses.get(target_comp.id, 0.0)
            total_weight_kg = max(0.1, total_weight_kg - removed_mass)
            trace.append(f"Action: Removed '{target_comp.name}' component (reduced UAV weight by {removed_mass:.2f} kg)")
            
            if "propeller" in target_comp.id:
                baseline_thrust *= 0.5
                trace.append("Propagated: lift thrust cut in half due to removed rotor assembly")
        
        elif mod_type == "change_material":
            new_mat_key = mod.get("value", "carbon_fiber")
            old_mat_key = self._map_material_name(target_comp.material)
            
            if new_mat_key in self.materials and old_mat_key in self.materials:
                density_old = self.materials[old_mat_key]["density"]
                density_new = self.materials[new_mat_key]["density"]
                old_mass = comp_masses.get(target_comp.id, 0.0)
                new_mass = old_mass * (density_new / density_old)
                
                comp_masses[target_comp.id] = new_mass
                total_weight_kg = total_weight_kg - old_mass + new_mass
                trace.append(f"Action: Swapped frame arm material to {new_mat_key}")
                trace.append(f"Propagated: weight adjusted from {old_mass:.2f} kg to {new_mass:.2f} kg")

        elif mod_type == "change_parameter":
            param_name = mod.get("parameter")
            param_val = mod.get("value")
            
            if param_name == "blades" and "propeller" in target_comp.id:
                try:
                    propeller_blades = int(param_val)
                    # Multi-blade scaling: 3-blade gives ~20% more thrust but increases torque/power draw by 35%
                    if propeller_blades == 3:
                        baseline_thrust *= 1.2
                        power_consumption_multiplier = 1.35
                        trace.append("Action: Configured 3-blade propeller array")
                        trace.append("Propagated: rotor thrust scaled up by 20.0%, torque power draw increased by 35.0%")
                    elif propeller_blades == 4:
                        baseline_thrust *= 1.35
                        power_consumption_multiplier = 1.6
                        trace.append("Action: Configured 4-blade propeller array")
                        trace.append("Propagated: rotor thrust scaled up by 35.0%, torque power draw increased by 60.0%")
                except Exception:
                    pass

        # Calculate dynamics
        thrust_to_weight = baseline_thrust / max(0.1, total_weight_kg)
        trace.append(f"Propagated: thrust-to-weight ratio computed at {thrust_to_weight:.2f}")

        # Flight time calculations
        if thrust_to_weight <= 1.0:
            flight_time_min = 0.0
            failure_risk_pct = 100.0
            warnings.append("CRITICAL: Thrust-to-weight ratio is <= 1.0! The quadcopter cannot generate sufficient lift to take off.")
            trace.append("Propagated: launch payload invalid; estimated flight duration dropped to 0.0 minutes")
        else:
            # Flight time decreases with TWR (heavy drone needs full throttle) and blade count power draw
            flight_time_min = max(2.0, (25.0 * (thrust_to_weight / 2.2) * (1.0 / power_consumption_multiplier)))
            # Clamp flight time
            flight_time_min = min(35.0, flight_time_min)
            trace.append(f"Propagated: flight duration evaluated at {flight_time_min:.1f} minutes")
            failure_risk_pct = 2.0
            
            if thrust_to_weight < 1.2:
                failure_risk_pct = 40.0
                warnings.append("WARNING: Weak thrust margin (TWR < 1.2). Maneuverability will be severely degraded.")
                trace.append("Propagated: poor structural control margin increased flight failure risk to 40.0%")

        metrics = {
            "total_weight_kg": round(total_weight_kg, 2),
            "thrust_to_weight_ratio": round(thrust_to_weight, 2),
            "propeller_blades": propeller_blades,
            "flight_time_min": round(flight_time_min, 1),
            "failure_risk_pct": round(failure_risk_pct, 1)
        }

        summary = f"Drone modification evaluated total weight at {total_weight_kg:.2f} kg, yielding flight time of {flight_time_min:.1f} minutes."
        return {
            "summary": summary,
            "metrics": metrics,
            "warnings": warnings,
            "trace": trace
        }

    def _run_generic_cascade(
        self, obj: Any, target_comp: Any, mod_type: str, mod: Dict[str, Any],
        comp_masses: Dict[str, float], total_weight_kg: float, trace: List[str], warnings: List[str]
    ) -> Dict[str, Any]:
        """Generic cascading simulation fallback."""
        if mod_type == "remove":
            removed_mass = comp_masses.get(target_comp.id, 0.0)
            total_weight_kg = max(0.0, total_weight_kg - removed_mass)
            trace.append(f"Action: Removed '{target_comp.name}' (reduced total weight to {total_weight_kg:.2f} kg)")
            if target_comp.parentId is None:
                warnings.append("CRITICAL: Removed root structural frame! The remaining assembly has no anchor.")
        elif mod_type == "change_material":
            new_mat = mod.get("value", "steel")
            trace.append(f"Action: Swapped material of '{target_comp.name}' to {new_mat}")

        metrics = {
            "total_weight_kg": round(total_weight_kg, 2),
            "failure_risk_pct": 5.0
        }
        return {
            "summary": f"Assembly weight shifted to {total_weight_kg:.2f} kg.",
            "metrics": metrics,
            "warnings": warnings,
            "trace": trace
        }
