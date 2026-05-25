import pytest
import math
from app.services.blender_service import BlenderService

def test_blender_script_generation_snapping_anchors():
    """Verify that attach_to configurations generate appropriate translation math in the Blender script."""
    service = BlenderService()
    components = [
        {
            "id": "cylinder_parent",
            "parentId": None,
            "position": [0.0, 0.0, 0.0],
            "geometry": {"type": "cylinder", "radius": 0.2, "depth": 1.5}
        },
        {
            "id": "box_child",
            "parentId": "cylinder_parent",
            "position": [0.0, 0.0, 0.0],
            "geometry": {"type": "box", "size": [0.3, 0.3, 0.3]},
            "attach_to": {
                "target": "cylinder_parent",
                "anchor": "front",
                "offset": [0.0, 0.1, 0.0]
            }
        }
    ]
    
    script = service._generate_blender_script(components, "test_output.glb")
    
    # Assert crucial attach variables are written in the script
    assert "attach = layout.get(\"attach_to\") or comp.get(\"attach_to\")" in script
    assert "target_id = attach.get(\"target\")" in script
    assert "anchor_name = attach.get(\"anchor\", \"top\")" in script
    assert "gtype = target_geom.get(\"type\", \"box\")" in script
    assert "anchor_offset = mathutils.Vector((0.0, depth / 2.0, 0.0))" in script
    assert "comp_world_mats.append(t_mat @ mathutils.Matrix.Translation(attach_local) @ local_rot_mat)" in script
