import os
import sys
import json
import logging
import subprocess
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BlenderService:
    """
    Compiles structural component specs into high-fidelity 3D GLB models 
    by programmatically invoking Blender in headless background mode.
    """

    def __init__(self, blender_path: str = None, cache_dir: str = None):
        from app.config import get_settings
        settings = get_settings()
        self.blender_path = blender_path or settings.BLENDER_PATH
        
        # Resolve absolute cache dir path
        base_dir = Path(__file__).resolve().parents[2]
        self.cache_dir = Path(cache_dir or settings.GLB_CACHE_DIR)
        if not self.cache_dir.is_absolute():
            self.cache_dir = base_dir / self.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def is_blender_available(self) -> bool:
        """Checks if the configured blender executable exists."""
        if not self.blender_path:
            return False
        return Path(self.blender_path).exists() or shutil.which(self.blender_path) is not None

    def get_model_cache_path(self, model_id: str) -> Path:
        """Returns the path to the cached GLB file for a given model ID."""
        return self.cache_dir / f"{model_id}.glb"

    async def compile_object(self, obj_data: Dict[str, Any]) -> str:
        """
        Compiles the explorable object component specs to a GLB file.
        Returns the filename (e.g. 'model_hash.glb') on success, or empty string on failure.
        """
        model_id = obj_data.get("id", "generic_object")
        components = obj_data.get("components", [])
        
        if not components:
            logger.warning("Cannot compile GLB: No components provided.")
            return ""

        # Check if Blender is installed
        if not self.is_blender_available():
            logger.warning(f"Blender executable not found at '{self.blender_path}'. Skipping mesh compilation.")
            return ""

        output_path = self.get_model_cache_path(model_id)
        
        # Generate the Blender python script content
        script_content = self._generate_blender_script(components, str(output_path))
        
        # Write script to a temporary file
        temp_script_path = self.cache_dir / f"compile_{model_id}.py"
        try:
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
                
            # Execute Blender headlessly
            logger.info(f"Invoking headless Blender to compile 3D model '{model_id}'...")
            cmd = [
                self.blender_path,
                "--background",
                "--python",
                str(temp_script_path)
            ]
            
            # Run the process
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30 # 30 seconds max execution time
            )
            
            if result.returncode != 0:
                logger.error(f"Blender compilation failed (code {result.returncode}):\n{result.stderr}")
                return ""
                
            logger.info(f"Successfully compiled 3D GLB model for '{model_id}' at {output_path}")
            return f"{model_id}.glb"
            
        except subprocess.TimeoutExpired:
            logger.error(f"Blender compilation timed out for '{model_id}'.")
            return ""
        except Exception as e:
            logger.error(f"Failed to compile 3D model via Blender: {e}")
            return ""
        finally:
            # Clean up temporary Python script
            if temp_script_path.exists():
                try:
                    temp_script_path.unlink()
                except Exception:
                    pass

    def _generate_blender_script(self, components: List[Dict[str, Any]], output_filepath: str) -> str:
        """Generates the Python script for Blender to construct the 3D scene."""
        escaped_filepath = output_filepath.replace("\\", "\\\\")
        
        # Start script with imports and cleanup
        script = f"""import bpy
import math

# Clear default objects
if bpy.ops.object.select_all:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_pbr_material(name, hex_color, material_type=""):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    if bsdf:
        # Convert hex color to RGBA
        hex_val = hex_color.lstrip('#')
        if len(hex_val) == 6:
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
            
        # PBR settings based on material name
        mat_lower = material_type.lower()
        if any(x in mat_lower for x in ["steel", "iron", "metal", "chrome", "alloy"]):
            bsdf.inputs['Metallic'].default_value = 0.9
            bsdf.inputs['Roughness'].default_value = 0.15
        elif any(x in mat_lower for x in ["copper", "brass", "bronze", "gold"]):
            bsdf.inputs['Metallic'].default_value = 0.95
            bsdf.inputs['Roughness'].default_value = 0.12
        elif any(x in mat_lower for x in ["glass", "lens", "optical"]):
            bsdf.inputs['Metallic'].default_value = 0.0
            bsdf.inputs['Roughness'].default_value = 0.05
            bsdf.inputs['Transmission'].default_value = 0.9
            # Enable blending for transparent export
            mat.blend_method = 'BLEND'
        elif any(x in mat_lower for x in ["rubber", "belt"]):
            bsdf.inputs['Metallic'].default_value = 0.0
            bsdf.inputs['Roughness'].default_value = 0.8
        else:
            bsdf.inputs['Metallic'].default_value = 0.4
            bsdf.inputs['Roughness'].default_value = 0.4
            
    return mat

def apply_transforms(obj, pos, rot):
    # Set position (ThreeJS Y-up to Blender Z-up)
    # Three.js: X (right), Y (up), Z (forward)
    # Blender: X (right), Y (forward), Z (up)
    # Mapping coordinates:
    obj.location = (pos[0], -pos[2], pos[1])
    
    # Set rotation
    obj.rotation_euler = (rot[0], -rot[2], rot[1])

def add_primitive(gtype, geom_data, name="part"):
    obj = None
    if gtype == "box" or gtype == "rounded_box":
        size = geom_data.get("size", [1, 1, 1])
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        obj = bpy.context.active_object
        obj.scale = (size[0], size[2], size[1])
        
    elif gtype == "cylinder" or gtype == "capsule":
        r = geom_data.get("radius", 0.5)
        d = geom_data.get("depth", 1.0)
        # Default Blender cylinder is aligned along Z. We rotate it to Y-up inside its frame
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, vertices=32)
        obj = bpy.context.active_object
        # Align to Y-up like ThreeJS
        obj.rotation_euler = (1.5708, 0, 0)
        
    elif gtype == "sphere":
        r = geom_data.get("radius", 0.5)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=32, ring_count=16)
        obj = bpy.context.active_object
        
    elif gtype == "cone":
        r = geom_data.get("radius", 0.5)
        d = geom_data.get("depth", 1.0)
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.0, depth=d)
        obj = bpy.context.active_object
        # Align to Y-up
        obj.rotation_euler = (1.5708, 0, 0)
        
    elif gtype == "torus":
        r = geom_data.get("radius", 0.5)
        t = geom_data.get("tube", 0.1)
        bpy.ops.mesh.primitive_torus_add(major_radius=max(0.01, r - t), minor_radius=t)
        obj = bpy.context.active_object
        
    elif gtype == "hemisphere":
        r = geom_data.get("radius", 0.5)
        # Blender doesn't have a hemisphere primitive. We add a sphere and bisect/delete half
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r)
        obj = bpy.context.active_object
        # Rotate to align hemisphere cap
        obj.rotation_euler = (1.5708, 0, 0)
        
    elif gtype == "fan":
        r = geom_data.get("radius", 0.5)
        blades = geom_data.get("blades", 6)
        # Combine central cylinder hub + array of blades
        bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.25, depth=0.1, vertices=16)
        hub = bpy.context.active_object
        hub.rotation_euler = (1.5708, 0, 0)
        
        # Create blade elements and join them
        for i in range(blades):
            angle = (2 * math.pi / blades) * i
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            blade = bpy.context.active_object
            blade.scale = (r * 0.9, 0.05, 0.02)
            # Center offset & rotate blade
            blade.location = (r * 0.45 * math.cos(angle), 0, r * 0.45 * math.sin(angle))
            blade.rotation_euler = (0, angle, 0.1) # Tilt blade for aero appearance
            
            # Join blade to hub
            blade.select_set(True)
            hub.select_set(True)
            bpy.context.view_layer.objects.active = hub
            bpy.ops.object.join()
        obj = hub
        
    elif gtype == "lathe":
        r = geom_data.get("radius", 0.5)
        d = geom_data.get("depth", 0.3)
        # Simple pulley/wheel proxy using a cylinder with a groove (mocked as box subtraction)
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d)
        obj = bpy.context.active_object
        obj.rotation_euler = (1.5708, 0, 0)
        
    if obj:
        obj.name = name
    return obj
"""
        
        # Loop through components and generate python construction logic
        for comp in components:
            cid = comp.get("id")
            cname = comp.get("name", cid)
            pos = comp.get("position", [0.0, 0.0, 0.0])
            rot = comp.get("rotation", [0.0, 0.0, 0.0])
            color = comp.get("color", "#c0c5ce")
            material = comp.get("material", "Steel")
            geometry = comp.get("geometry", {})
            gtype = geometry.get("type", "box")
            
            # Skip parent children link logic since Blender handles absolute positions
            script += f"""
# --- Add Component: {cname} ({cid}) ---
try:
    mat_{cid} = create_pbr_material("mat_{cid}", "{color}", "{material}")
"""
            
            # CSG Boolean Subtractions Handling
            if gtype == "csg":
                base_geom = geometry.get("base", {"type": "box"})
                subtractions = geometry.get("subtractions", [])
                
                script += f"""
    # CSG Base
    base_obj = add_primitive("{base_geom.get('type', 'box')}", {json.dumps(base_geom)}, "{cid}_base")
    if base_obj:
        base_obj.data.materials.append(mat_{cid})
        
        # Subtractions
"""
                for idx, sub in enumerate(subtractions):
                    sub_pos = sub.get("position", [0.0, 0.0, 0.0])
                    sub_rot = sub.get("rotation", [0.0, 0.0, 0.0])
                    script += f"""
        # Cut {idx}
        cut_obj = add_primitive("{sub.get('type')}", {json.dumps(sub)}, "{cid}_cut_{idx}")
        if cut_obj:
            apply_transforms(cut_obj, {sub_pos}, {sub_rot})
            
            # Add modifier to base
            bool_mod = base_obj.modifiers.new(name="bool_{idx}", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = cut_obj
            
            # Apply Boolean modifier
            bpy.context.view_layer.objects.active = base_obj
            bpy.ops.object.modifier_apply(modifier="bool_{idx}")
            
            # Remove cutting mesh
            bpy.data.objects.remove(cut_obj, do_unlink=True)
"""
                # Transform the final compound CSG object
                script += f"""
        apply_transforms(base_obj, {pos}, {rot})
"""
                
            else:
                # Standard Primitives
                script += f"""
    obj = add_primitive("{gtype}", {json.dumps(geometry)}, "{cid}")
    if obj:
        obj.data.materials.append(mat_{cid})
        apply_transforms(obj, {pos}, {rot})
"""
            script += """
except Exception as e:
    print(f"Error constructing component {cid}: {e}")
"""

        # Export scene to GLB
        script += f"""
# Export scene to GLB
try:
    print("Exporting GLB scene...")
    bpy.ops.export_scene.gltf(
        filepath="{escaped_filepath}",
        export_format='GLB',
        use_selection=False,
        export_materials='EXPORT',
        export_colors=True
    )
    print("Export complete.")
except Exception as e:
    print(f"Export failed: {{e}}")
"""
        return script
