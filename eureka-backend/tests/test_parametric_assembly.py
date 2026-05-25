import json
from app.services.blender_service import BlenderService, topological_sort
from app.agents.object_architect_agent import ObjectArchitectAgent
from app.services.ollama_service import OllamaService
from unittest.mock import MagicMock

def test_topological_sort():
    """Verify that topological_sort correctly orders dependencies (parents before children)."""
    components = [
        {"id": "blade", "parentId": "hub"},
        {"id": "hub", "parentId": "shaft"},
        {"id": "shaft", "parentId": None},
        {"id": "casing", "parentId": None}
    ]
    
    sorted_comps = topological_sort(components)
    
    # Create mapping of ID to its index in sorted list
    indices = {c["id"]: idx for idx, c in enumerate(sorted_comps)}
    
    assert indices["shaft"] < indices["hub"]
    assert indices["hub"] < indices["blade"]
    # casing is independent, but must be present
    assert "casing" in indices

def test_blender_script_generation_radial():
    """Verify that radial arrays generate valid matrices and rotation logic in the Blender script."""
    service = BlenderService()
    components = [
        {
            "id": "shaft",
            "parentId": None,
            "position": [0, 0, 0],
            "geometry": {"type": "cylinder", "radius": 0.1, "depth": 2.0}
        },
        {
            "id": "blade",
            "parentId": "shaft",
            "position": [0, 0.5, 0],
            "geometry": {"type": "box", "size": [0.4, 0.05, 0.1]},
            "layout": {
                "type": "radial_array",
                "count": 6,
                "radius": 0.5,
                "center": [0, 0, 0],
                "axis": "Y"
            }
        }
    ]
    
    script = service._generate_blender_script(components, "test_output.glb")
    
    # Assert key mathematical constructs are outputted in the script
    assert "radial_array" in script
    assert "angle = (2 * math.pi / count) * i" in script
    assert "radius * math.cos(angle)" in script
    assert "radius * math.sin(angle)" in script
    assert "Euler((0.0, 0.0, angle))" in script
    assert "align_mat = mathutils.Euler((1.5708, 0, 0)).to_matrix().to_4x4()" in script

def test_blender_script_generation_linear():
    """Verify that linear arrays generate correct spacing variables and translations."""
    service = BlenderService()
    components = [
        {
            "id": "engine_block",
            "parentId": None,
            "position": [0, 0, 0],
            "geometry": {"type": "box", "size": [1.0, 0.5, 0.5]}
        },
        {
            "id": "piston",
            "parentId": "engine_block",
            "position": [0, 0.2, 0],
            "geometry": {"type": "cylinder", "radius": 0.1, "depth": 0.3},
            "layout": {
                "type": "linear_array",
                "count": 4,
                "spacing": [0.25, 0.0, 0.0],
                "start": [-0.375, 0, 0]
            }
        }
    ]
    
    script = service._generate_blender_script(components, "test_output.glb")
    
    assert "linear_array" in script
    assert "offset = b_start + i * b_spacing" in script
    assert "mathutils.Matrix.Translation(offset)" in script

def test_blender_script_generation_mirror():
    """Verify that bilateral mirrors produce correct scale matrices."""
    service = BlenderService()
    components = [
        {
            "id": "chassis",
            "parentId": None,
            "position": [0, 0, 0],
            "geometry": {"type": "box", "size": [2.0, 0.2, 1.0]}
        },
        {
            "id": "wing",
            "parentId": "chassis",
            "position": [1.0, 0, 0],
            "geometry": {"type": "box", "size": [1.0, 0.05, 0.3]},
            "layout": {
                "type": "mirror",
                "axis": "X"
            }
        }
    ]
    
    script = service._generate_blender_script(components, "test_output.glb")
    
    assert "mirror" in script
    assert "mirror_scale = mathutils.Vector((1, 1, 1))" in script
    assert "mirror_scale[0] = -1" in script
    assert "mathutils.Matrix.Scale(-1, 4, mirror_scale)" in script

def test_fallback_preset_layouts():
    """Verify that fallback presets define correct relationships (layout field) rather than raw hardcoded positions."""
    mock_ollama = MagicMock(spec=OllamaService)
    agent = ObjectArchitectAgent(mock_ollama)
    
    drone = agent.generate_fallback_object("quadcopter")
    # Verify drone layout operators
    arms = [c for c in drone.components if c.id == "arm"]
    assert len(arms) == 1  # Should only have 1 logical arm definition with a radial layout operator
    assert arms[0].geometry.get("type") == "cylinder"
    assert arms[0].layout is not None
    assert arms[0].layout["type"] == "radial_array"
    assert arms[0].layout["count"] == 4
    
    motors = [c for c in drone.components if c.id == "motor"]
    assert len(motors) == 1
    assert motors[0].parent_id == "arm"
    
    props = [c for c in drone.components if c.id == "propeller"]
    assert len(props) == 1
    assert props[0].parent_id == "motor"
    
    # Engine
    engine = agent.generate_fallback_object("car engine")
    pistons = [c for c in engine.components if c.id == "piston"]
    assert len(pistons) == 1
    assert pistons[0].layout is not None
    assert pistons[0].layout["type"] == "linear_array"
    assert pistons[0].layout["count"] == 4
