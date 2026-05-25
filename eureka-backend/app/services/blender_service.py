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

def topological_sort(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_comps = []
    visited = set()
    comp_dict = {c["id"]: c for c in components if c.get("id")}
    
    def visit(cid):
        if cid in visited:
            return
        visited.add(cid)
        comp = comp_dict.get(cid)
        if not comp:
            return
        pid = comp.get("parentId")
        if pid and pid in comp_dict:
            visit(pid)
        sorted_comps.append(comp)
        
    for comp in components:
        if comp.get("id"):
            visit(comp["id"])
    return sorted_comps

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
        parameters = obj_data.get("parameters", {})
        
        if not components:
            logger.warning("Cannot compile GLB: No components provided.")
            return ""

        # Check if Blender is installed
        if not self.is_blender_available():
            logger.warning(f"Blender executable not found at '{self.blender_path}'. Skipping mesh compilation.")
            return ""

        # Solve relative expressions and evaluate CAD dimensions
        from app.services.parameter_resolver import resolve_parametric_object
        try:
            resolved_components = resolve_parametric_object(components, parameters)
        except Exception as e:
            logger.error(f"Parametric resolution failed during compilation: {e}")
            return ""

        output_path = self.get_model_cache_path(model_id)
        
        # Generate the Blender python script content
        script_content = self._generate_blender_script(resolved_components, str(output_path))
        
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
        
        # Sort components topologically (parents before children)
        sorted_comps = topological_sort(components)
        comp_json_str = json.dumps(sorted_comps)
        
        # Start script with imports and helpers
        script = f"""import bpy
import math
import mathutils
import json

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
            mat.blend_method = 'BLEND'
        elif any(x in mat_lower for x in ["rubber", "belt"]):
            bsdf.inputs['Metallic'].default_value = 0.0
            bsdf.inputs['Roughness'].default_value = 0.8
        else:
            bsdf.inputs['Metallic'].default_value = 0.4
            bsdf.inputs['Roughness'].default_value = 0.4
            
    return mat

def make_blender_matrix(pos, rot):
    # Convert position (ThreeJS Y-up to Blender Z-up)
    # ThreeJS (x, y, z) -> Blender (x, -z, y)
    b_pos = mathutils.Vector((pos[0], -pos[2], pos[1]))
    # Convert rotation (Euler)
    b_rot = mathutils.Euler((rot[0], -rot[2], rot[1]))
    return mathutils.Matrix.Translation(b_pos) @ b_rot.to_matrix().to_4x4()

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
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, vertices=32)
        obj = bpy.context.active_object
        
    elif gtype == "sphere":
        r = geom_data.get("radius", 0.5)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=32, ring_count=16)
        obj = bpy.context.active_object
        
    elif gtype == "cone":
        r = geom_data.get("radius", 0.5)
        d = geom_data.get("depth", 1.0)
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.0, depth=d)
        obj = bpy.context.active_object
        
    elif gtype == "torus":
        r = geom_data.get("radius", 0.5)
        t = geom_data.get("tube", 0.1)
        bpy.ops.mesh.primitive_torus_add(major_radius=max(0.01, r - t), minor_radius=t)
        obj = bpy.context.active_object
        
    elif gtype == "hemisphere":
        r = geom_data.get("radius", 0.5)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r)
        obj = bpy.context.active_object
        
    elif gtype == "fan":
        r = geom_data.get("radius", 0.5)
        blades = geom_data.get("blades", 6)
        bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.25, depth=0.1, vertices=16)
        hub = bpy.context.active_object
        
        for i in range(blades):
            angle = (2 * math.pi / blades) * i
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            blade = bpy.context.active_object
            blade.scale = (r * 0.9, 0.05, 0.02)
            blade.location = (r * 0.45 * math.cos(angle), 0, r * 0.45 * math.sin(angle))
            blade.rotation_euler = (0, angle, 0.1)
            
            blade.select_set(True)
            hub.select_set(True)
            bpy.context.view_layer.objects.active = hub
            bpy.ops.object.join()
        obj = hub
        
    elif gtype == "lathe":
        r = geom_data.get("radius", 0.5)
        d = geom_data.get("depth", 0.3)
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d)
        obj = bpy.context.active_object
        
    elif gtype == "csg":
        base_geom = geom_data.get("base", {{"type": "box"}})
        subtractions = geom_data.get("subtractions", [])
        base_obj = add_primitive(base_geom.get("type", "box"), base_geom, f"{{name}}_base")
        if base_obj:
            for idx, sub in enumerate(subtractions):
                sub_type = sub.get("type", "cylinder")
                sub_pos = sub.get("position", [0.0, 0.0, 0.0])
                sub_rot = sub.get("rotation", [0.0, 0.0, 0.0])
                
                cut_obj = add_primitive(sub_type, sub, f"{{name}}_cut_{{idx}}")
                if cut_obj:
                    cut_pos = mathutils.Vector((sub_pos[0], -sub_pos[2], sub_pos[1]))
                    cut_rot = mathutils.Euler((sub_rot[0], -sub_rot[2], sub_rot[1]))
                    cut_align = mathutils.Matrix.Identity(4)
                    if sub_type in ["cylinder", "capsule", "cone", "hemisphere", "fan", "lathe"]:
                        cut_align = mathutils.Euler((1.5708, 0, 0)).to_matrix().to_4x4()
                    
                    cut_obj.matrix_world = mathutils.Matrix.Translation(cut_pos) @ cut_rot.to_matrix().to_4x4() @ cut_align
                    
                    bool_mod = base_obj.modifiers.new(name=f"bool_{{idx}}", type='BOOLEAN')
                    bool_mod.operation = 'DIFFERENCE'
                    bool_mod.object = cut_obj
                    
                    bpy.context.view_layer.objects.active = base_obj
                    bpy.ops.object.modifier_apply(modifier=f"bool_{{idx}}")
                    bpy.data.objects.remove(cut_obj, do_unlink=True)
            obj = base_obj
            
    if obj:
        obj.name = name
    return obj

# Components definitions JSON
components_data = json.loads(r'''{comp_json_str}''')

world_matrices = {{}}

for comp in components_data:
    cid = comp["id"]
    pid = comp.get("parentId")
    
    # 1. Parent matrices
    if not pid or pid not in world_matrices:
        parent_mats = [mathutils.Matrix.Identity(4)]
    else:
        parent_mats = world_matrices[pid]
        
    # 2. Local matrix
    pos = comp.get("position", [0.0, 0.0, 0.0])
    rot = comp.get("rotation", [0.0, 0.0, 0.0])
    local_mat = make_blender_matrix(pos, rot)
    
    # 3. Layout Arrays or Snapping Anchor alignment
    layout = comp.get("layout", {{}})
    attach = layout.get("attach_to") or comp.get("attach_to")
    
    comp_world_mats = []
    
    if attach:
        target_id = attach.get("target")
        if target_id == "parent":
            target_id = pid
            
        if target_id and target_id in world_matrices:
            target_mats = world_matrices[target_id]
            target_comp = next((c for c in components_data if c["id"] == target_id), None)
            target_geom = target_comp.get("geometry", {{}}) if target_comp else {{}}
            
            anchor_name = attach.get("anchor", "top")
            offset = attach.get("offset", [0.0, 0.0, 0.0])
            offset_vec = mathutils.Vector((offset[0], offset[1], offset[2]))
            
            gtype = target_geom.get("type", "box")
            anchor_offset = mathutils.Vector((0.0, 0.0, 0.0))
            
            if gtype in ["cylinder", "capsule", "cone", "lathe", "fan"]:
                depth = target_geom.get("depth", 1.0)
                radius = target_geom.get("radius", 0.5)
                if anchor_name in ["front", "top"]:
                    anchor_offset = mathutils.Vector((0.0, depth / 2.0, 0.0))
                elif anchor_name in ["back", "bottom"]:
                    anchor_offset = mathutils.Vector((0.0, -depth / 2.0, 0.0))
                elif anchor_name in ["radial", "right"]:
                    anchor_offset = mathutils.Vector((radius, 0.0, 0.0))
                elif anchor_name == "left":
                    anchor_offset = mathutils.Vector((-radius, 0.0, 0.0))
                    
            elif gtype in ["box", "rounded_box"]:
                size = target_geom.get("size", [1.0, 1.0, 1.0])
                w, h, d = size[0], size[1], size[2]
                if anchor_name == "top":
                    anchor_offset = mathutils.Vector((0.0, h / 2.0, 0.0))
                elif anchor_name == "bottom":
                    anchor_offset = mathutils.Vector((0.0, -h / 2.0, 0.0))
                elif anchor_name == "right":
                    anchor_offset = mathutils.Vector((w / 2.0, 0.0, 0.0))
                elif anchor_name == "left":
                    anchor_offset = mathutils.Vector((-w / 2.0, 0.0, 0.0))
                elif anchor_name == "front":
                    anchor_offset = mathutils.Vector((0.0, 0.0, d / 2.0))
                elif anchor_name == "back":
                    anchor_offset = mathutils.Vector((0.0, 0.0, -d / 2.0))
                    
            elif gtype in ["sphere", "hemisphere"]:
                radius = target_geom.get("radius", 0.5)
                if anchor_name in ["top", "front"]:
                    anchor_offset = mathutils.Vector((0.0, radius, 0.0))
                elif anchor_name in ["bottom", "back"]:
                    anchor_offset = mathutils.Vector((0.0, -radius, 0.0))
                elif anchor_name == "right":
                    anchor_offset = mathutils.Vector((radius, 0.0, 0.0))
                elif anchor_name == "left":
                    anchor_offset = mathutils.Vector((-radius, 0.0, 0.0))
            
            attach_local = anchor_offset + offset_vec
            
            # Extract local rotation of component
            rot = comp.get("rotation", [0.0, 0.0, 0.0])
            b_rot = mathutils.Euler((rot[0], -rot[2], rot[1]))
            local_rot_mat = b_rot.to_matrix().to_4x4()
            
            for t_mat in target_mats:
                comp_world_mats.append(t_mat @ mathutils.Matrix.Translation(attach_local) @ local_rot_mat)
        else:
            comp_world_mats = [mathutils.Matrix.Identity(4)]
            
    else:
        layout_type = layout.get("type")
        layout_mats = []
        
        if layout_type == "radial_array":
            count = layout.get("count", 4)
            radius = layout.get("radius", 1.0)
            center = layout.get("center", [0.0, 0.0, 0.0])
            axis = layout.get("axis", "Y")
            b_center = mathutils.Vector((center[0], -center[2], center[1]))
            
            for i in range(count):
                angle = (2 * math.pi / count) * i
                if axis == "Y":
                    loc = mathutils.Vector((radius * math.cos(angle), radius * math.sin(angle), 0.0)) + b_center
                    rot_mat = mathutils.Euler((0.0, 0.0, angle)).to_matrix().to_4x4()
                elif axis == "Z":
                    loc = mathutils.Vector((radius * math.cos(angle), 0.0, radius * math.sin(angle))) + b_center
                    rot_mat = mathutils.Euler((0.0, angle, 0.0)).to_matrix().to_4x4()
                else:
                    loc = mathutils.Vector((0.0, radius * math.cos(angle), radius * math.sin(angle))) + b_center
                    rot_mat = mathutils.Euler((angle, 0.0, 0.0)).to_matrix().to_4x4()
                
                layout_mats.append(mathutils.Matrix.Translation(loc) @ rot_mat)
                
        elif layout_type == "linear_array":
            count = layout.get("count", 4)
            spacing = layout.get("spacing", [0.2, 0.0, 0.0])
            start = layout.get("start", [0.0, 0.0, 0.0])
            
            b_spacing = mathutils.Vector((spacing[0], -spacing[2], spacing[1]))
            b_start = mathutils.Vector((start[0], -start[2], start[1]))
            
            for i in range(count):
                offset = b_start + i * b_spacing
                layout_mats.append(mathutils.Matrix.Translation(offset))
                
        elif layout_type == "mirror":
            axis = layout.get("axis", "X")
            mirror_scale = mathutils.Vector((1, 1, 1))
            if axis == "X":
                mirror_scale[0] = -1
            elif axis == "Y":
                mirror_scale[2] = -1
            else:
                mirror_scale[1] = -1
                
            mirror_mat = mathutils.Matrix.Scale(-1, 4, mirror_scale)
            layout_mats.append(mathutils.Matrix.Identity(4))
            layout_mats.append(mirror_mat)
            
        else:
            layout_mats.append(mathutils.Matrix.Identity(4))
            
        for p_mat in parent_mats:
            for l_mat in layout_mats:
                comp_world_mats.append(p_mat @ l_mat @ local_mat)
                
    world_matrices[cid] = comp_world_mats
    
    # 5. Render components
    geometry = comp.get("geometry", {{}})
    gtype = geometry.get("type", "box")
    
    if gtype == "empty" or gtype == "none":
        continue
        
    color = comp.get("color", "#c0c5ce")
    material_name = comp.get("material", "Steel")
    mat = create_pbr_material(f"mat_{{cid}}", color, material_name)
    
    align_mat = mathutils.Matrix.Identity(4)
    if gtype in ["cylinder", "capsule", "cone", "hemisphere", "fan", "lathe"]:
        align_mat = mathutils.Euler((1.5708, 0, 0)).to_matrix().to_4x4()
        
    for idx, w_mat in enumerate(comp_world_mats):
        obj = add_primitive(gtype, geometry, f"{{cid}}_{{idx}}")
        if obj:
            obj.matrix_world = w_mat @ align_mat
            obj.data.materials.append(mat)

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
