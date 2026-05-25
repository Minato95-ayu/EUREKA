import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json

from main import app
from app.services.dependency_engine import DependencyEngine
from app.api.experiments import WhatIfRequest

client = TestClient(app)

@pytest.fixture
def temp_materials_file(tmp_path):
    """Fixture to create a temporary materials file for testing."""
    file_path = tmp_path / "materials.json"
    data = {
        "aluminum_alloy": {
            "name": "Aluminum Alloy",
            "density": 2.7,
            "thermal_conductivity": 167.0,
            "thermal_limit": 300.0,
            "yield_strength": 276.0,
            "youngs_modulus": 68.9,
            "cte": 23.6
        },
        "steel": {
            "name": "Steel",
            "density": 7.85,
            "thermal_conductivity": 50.0,
            "thermal_limit": 1200.0,
            "yield_strength": 415.0,
            "youngs_modulus": 200.0,
            "cte": 12.0
        },
        "cast_iron": {
            "name": "Cast Iron",
            "density": 7.2,
            "thermal_conductivity": 53.0,
            "thermal_limit": 1150.0,
            "yield_strength": 240.0,
            "youngs_modulus": 110.0,
            "cte": 11.0
        },
        "carbon_fiber": {
            "name": "Carbon Fiber",
            "density": 1.6,
            "thermal_conductivity": 5.0,
            "thermal_limit": 400.0,
            "yield_strength": 900.0,
            "youngs_modulus": 135.0,
            "cte": -0.5
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path

def test_load_materials(temp_materials_file):
    """Verify that materials database loads successfully."""
    engine = DependencyEngine(materials_path=temp_materials_file)
    assert len(engine.materials) == 4
    assert engine.materials["aluminum_alloy"]["density"] == 2.7
    assert engine.materials["steel"]["thermal_limit"] == 1200.0

def test_engine_component_removal(temp_materials_file):
    """Verify removing cooling_fan triggers cascading thermodynamic and lubrication failure traces."""
    engine = DependencyEngine(materials_path=temp_materials_file)
    # Using 'car_engine' which is loaded from the preset demo objects fallback library
    res = engine.evaluate_modification("car_engine", "cooling_fan", {"type": "remove"})
    
    assert "metrics" in res
    assert "trace" in res
    assert "warnings" in res
    
    metrics = res["metrics"]
    trace = res["trace"]
    warnings = res["warnings"]
    
    # Assert cascade calculations
    assert metrics["cooling_efficiency_pct"] == 20.0
    assert metrics["temperature_c"] == 149.0
    assert metrics["oil_viscosity_pct"] < 50.0
    assert metrics["friction_multiplier"] > 2.0
    assert metrics["rpm_stability_pct"] < 80.0
    assert metrics["failure_risk_pct"] > 80.0
    
    # Assert causal trace has propagated correctly
    assert any("Action: Removed 'Cooling Fan'" in step or "cooling_fan" in step.lower() for step in trace)
    assert any("cooling_efficiency_pct decreased" in step or "cooling_efficiency" in step.lower() for step in trace)
    assert any("oil viscosity degraded" in step or "oil_viscosity" in step.lower() for step in trace)
    assert any("friction" in step.lower() for step in trace)
    assert any("failure risk" in step.lower() for step in trace)
    
    # Assert critical warnings are present
    assert any("viscosity" in w.lower() or "overheat" in w.lower() or "seizure" in w.lower() for w in warnings)

def test_engine_material_change(temp_materials_file):
    """Verify that changing piston material modifies reciprocating properties and mass correctly."""
    engine = DependencyEngine(materials_path=temp_materials_file)
    
    # 1. Change piston material to heavier cast_iron
    res_heavy = engine.evaluate_modification("car_engine", "piston", {"type": "change_material", "value": "cast_iron"})
    weight_heavy = res_heavy["metrics"]["total_weight_kg"]
    safe_rpm_heavy = res_heavy["metrics"]["max_safe_rpm"]
    
    # 2. Change piston material to lighter carbon_fiber
    res_light = engine.evaluate_modification("car_engine", "piston", {"type": "change_material", "value": "carbon_fiber"})
    weight_light = res_light["metrics"]["total_weight_kg"]
    safe_rpm_light = res_light["metrics"]["max_safe_rpm"]
    
    # Lighter piston should result in lower total weight and higher safe operating speed (RPM)
    assert weight_light < weight_heavy
    assert safe_rpm_light > safe_rpm_heavy

def test_drone_material_change(temp_materials_file, tmp_path):
    """Verify that changing frame arm material to steel plummets drone thrust-to-weight and flight time."""
    from app.agents.object_architect_agent import ObjectArchitectAgent
    from app.services.ollama_service import OllamaService
    from unittest.mock import MagicMock
    
    # Generate and save quadcopter drone fallback to temp repository
    agent = ObjectArchitectAgent(MagicMock(spec=OllamaService), library_dir=tmp_path)
    drone = agent.generate_fallback_object("quadcopter")
    agent.repository.save_object(drone)
    
    engine = DependencyEngine(materials_path=temp_materials_file, library_dir=tmp_path)
    
    # Drone arm swapped to heavy steel
    res = engine.evaluate_modification("drone", "arm", {"type": "change_material", "value": "steel"})
    metrics = res["metrics"]
    
    # Should prevent flight
    assert metrics["thrust_to_weight_ratio"] <= 1.0
    assert metrics["flight_time_min"] == 0.0
    assert metrics["failure_risk_pct"] == 100.0
    assert len(res["warnings"]) > 0

def test_drone_parameter_change(temp_materials_file, tmp_path):
    """Verify that increasing drone propeller blade count scales thrust but drains battery flight time."""
    from app.agents.object_architect_agent import ObjectArchitectAgent
    from app.services.ollama_service import OllamaService
    from unittest.mock import MagicMock
    
    # Generate and save quadcopter drone fallback to temp repository
    agent = ObjectArchitectAgent(MagicMock(spec=OllamaService), library_dir=tmp_path)
    drone = agent.generate_fallback_object("quadcopter")
    agent.repository.save_object(drone)
    
    engine = DependencyEngine(materials_path=temp_materials_file, library_dir=tmp_path)
    
    # Swap blades of rotor assembly to 3 blades
    res = engine.evaluate_modification("drone", "propeller", {"type": "change_parameter", "parameter": "blades", "value": "3"})
    metrics = res["metrics"]
    
    assert metrics["propeller_blades"] == 3
    assert metrics["thrust_to_weight_ratio"] > 1.3 # increased from baseline TWR of 1.22
    assert metrics["flight_time_min"] < 25.0 # baseline flight time drained due to power load

def test_api_what_if_endpoint():
    """Verify that POST /api/experiments/what-if works and handles errors correctly."""
    # Test valid simulation request
    response = client.post(
        "/api/experiments/what-if",
        json={
            "objectId": "car_engine",
            "componentId": "cooling_fan",
            "modification": {"type": "remove"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "metrics" in data
    assert "trace" in data
    assert len(data["trace"]) > 0
    
    # Test invalid object ID
    response_invalid = client.post(
        "/api/experiments/what-if",
        json={
            "objectId": "non_existent_engine",
            "componentId": "cooling_fan",
            "modification": {"type": "remove"}
        }
    )
    assert response_invalid.status_code == 400
