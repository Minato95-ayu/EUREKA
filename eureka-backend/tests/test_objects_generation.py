import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import json
import math

from main import app
from app.agents.object_architect_agent import ObjectArchitectAgent
from app.models.object_graph import ExplorableObject
from app.services.ollama_service import OllamaService

def test_api_generate_fallback():
    """Verify that when no LLM is running or it times out, the API gracefully returns a fallback object."""
    client = TestClient(app)
    response = client.post("/api/objects/generate?q=drone")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "drone"
    assert data["name"] == "Quadcopter Drone"
    assert len(data["components"]) > 0
    
    # Check parent child consistency
    components = data["components"]
    root_nodes = [c for c in components if c["parentId"] is None]
    assert len(root_nodes) == 1
    
    # Verify simulation properties exist on the components
    for comp in components:
        assert "simulationProperties" in comp
        assert "mass" in comp["simulationProperties"]
        assert "heatGeneration" in comp["simulationProperties"]
        assert "energyConsumption" in comp["simulationProperties"]

def test_fallback_presets():
    """Verify all fallback presets (drone, engine, microscope, generic) compile to valid ExplorableObject models."""
    mock_ollama = MagicMock(spec=OllamaService)
    agent = ObjectArchitectAgent(mock_ollama)
    
    # Drone
    drone = agent.generate_fallback_object("quadcopter")
    assert drone.id == "drone"
    assert len(drone.components) == 13  # Chassis + 4 arms + 4 motors + 4 props
    
    # Engine
    engine = agent.generate_fallback_object("car engine")
    assert engine.id == "car_engine"
    assert len(engine.components) == 14  # Engine block, head, oil pan, crankshaft, flywheel, 4 pistons, 4 rods, fan
    
    # Microscope
    scope = agent.generate_fallback_object("microscope")
    assert scope.id == "microscope"
    assert len(scope.components) == 4
    
    # Generic
    generic = agent.generate_fallback_object("solar panel")
    assert generic.id == "solar_panel"
    assert len(generic.components) == 3

def test_rule_engine_structural_cleaning():
    """Verify rule engine enforces acyclic layout, root coordinates, NaN checking, and link consistency."""
    mock_ollama = MagicMock(spec=OllamaService)
    agent = ObjectArchitectAgent(mock_ollama)
    
    malformed_payload = {
        "id": "broken_machine",
        "name": "Broken Machine",
        "type": "mechanical_system",
        "summary": "Testing structural fixing",
        "components": [
            {
                "id": "root_part",
                "name": "Root Part",
                "parentId": None,
                "position": [float('nan'), 2.0, 0.0],  # NaN position
                "geometry": {"type": "invalid_shape", "size": [1.0]}  # Invalid type and size array
            },
            {
                "id": "child_part",
                "name": "Child Part",
                "parentId": "root_part",
                # missing geometry
            }
        ]
    }
    
    cleaned = agent._apply_rule_engine(malformed_payload, "broken_machine")
    
    # Verify NaN corrected
    assert cleaned["components"][0]["position"] == [0.0, 0.0, 0.0]
    
    # Verify invalid geometry corrected
    assert cleaned["components"][0]["geometry"]["type"] == "box"
    assert cleaned["components"][0]["geometry"]["size"] == [1.0, 1.0, 1.0]
    
    # Verify child parent linked
    assert "child_part" in cleaned["components"][0]["children"]
    assert cleaned["components"][1]["parentId"] == "root_part"

@pytest.mark.asyncio
async def test_successful_llm_generation_with_caching(tmp_path):
    """Mock the Ollama service to verify caching and LLM parser success path."""
    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.generate = AsyncMock(return_value=json.dumps({
        "id": "hovercraft",
        "name": "Sci-Fi Hovercraft",
        "type": "mechanical_system",
        "summary": "An LLM generated hovercraft.",
        "components": [
            {
                "id": "hull",
                "name": "Main Hull",
                "parentId": None,
                "scaleLevel": "component",
                "function": "Main chassis",
                "position": [0.0, 0.0, 0.0],
                "color": "#333333",
                "geometry": {"type": "box", "size": [3.0, 1.0, 2.0]},
                "simulationProperties": {"mass": 500.0, "heatGeneration": 0.1, "energyConsumption": 0.2}
            }
        ]
    }))
    
    agent = ObjectArchitectAgent(mock_ollama)
    # Redirect cache dir to tmp_path
    agent.cache_dir = tmp_path
    
    # First invocation should hit the mock LLM
    obj = await agent.generate_object("hovercraft")
    assert obj.id == "hovercraft"
    assert len(obj.components) == 1
    mock_ollama.generate.assert_called_once()
    
    # Verify file was cached
    cache_file = agent._get_cache_path("hovercraft")
    assert cache_file.exists()
    
    # Reset mock and call again; should hit cache and NOT mock LLM
    mock_ollama.generate.reset_mock()
    obj_cached = await agent.generate_object("hovercraft")
    assert obj_cached.id == "hovercraft"
    mock_ollama.generate.assert_not_called()
