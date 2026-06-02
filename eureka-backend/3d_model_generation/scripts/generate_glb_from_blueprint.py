"""
Generate a simple low-GPU GLB model from an Eureka object blueprint.

Run with Blender:
  blender --background --python generate_glb_from_blueprint.py -- \
    ../examples/car_engine.blueprint.json ../../static/models/generated/car_engine.glb

This script stays isolated from the backend runtime. It is meant to become the
first worker step for search-to-3D generation jobs.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy


UNIT_TO_METERS = {
    "um": 0.000001,
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
}


MATERIAL_COLORS = {
    "aluminum": (0.74, 0.76, 0.78, 1.0),
    "iron": (0.28, 0.29, 0.30, 1.0),
    "steel": (0.50, 0.53, 0.56, 1.0),
    "composite": (0.12, 0.14, 0.16, 1.0),
    "rubber": (0.02, 0.02, 0.02, 1.0),
    "default": (0.42, 0.58, 0.72, 1.0),
}


def parse_args() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit("Expected args after --: <blueprint.json> <output.glb>")

    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 2:
        raise SystemExit("Usage: blender --background --python script.py -- <blueprint.json> <output.glb>")

    return Path(args[0]).resolve(), Path(args[1]).resolve()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def meters(value: float | int | None, unit: str) -> float:
    if value is None:
        return 0.1
    return float(value) * UNIT_TO_METERS.get(unit, 1.0)


def material_for(name: str | None) -> bpy.types.Material:
    key = "default"
    if name:
        material_name = name.lower()
        for candidate in MATERIAL_COLORS:
            if candidate in material_name:
                key = candidate
                break

    mat = bpy.data.materials.get(f"eureka_{key}")
    if mat:
        return mat

    mat = bpy.data.materials.new(f"eureka_{key}")
    mat.diffuse_color = MATERIAL_COLORS[key]
    return mat


def add_box(name: str, scale: dict, material_name: str | None, location: tuple[float, float, float]) -> bpy.types.Object:
    unit = scale.get("unit", "cm")
    length = max(meters(scale.get("length"), unit), 0.03)
    width = max(meters(scale.get("width"), unit), 0.03)
    height = max(meters(scale.get("height"), unit), 0.03)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (length, width, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material_for(material_name))
    return obj


def add_cylinder(
    name: str,
    scale: dict,
    material_name: str | None,
    location: tuple[float, float, float],
    rotate_x: bool = False,
) -> bpy.types.Object:
    unit = scale.get("unit", "cm")
    radius = max(meters(scale.get("diameter"), unit) / 2.0, 0.015)
    depth = max(meters(scale.get("height") or scale.get("length"), unit), 0.04)

    rotation = (math.radians(90), 0, 0) if rotate_x else (0, 0, 0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material_for(material_name))
    return obj


def component_shape(component: dict) -> str:
    name = component.get("name", "").lower()
    if "cylinder" in name or "shaft" in name or "piston" in name:
        return "cylinder"
    return "box"


def add_component(component: dict, index: int, total: int, parent_x: float = 0.0, z: float = 0.0) -> None:
    scale = component.get("realScale") or {"unit": "cm", "length": 10, "width": 8, "height": 8}
    span = max(total - 1, 1)
    x = parent_x + (index - span / 2.0) * 0.16
    y = 0.0
    name = component.get("name", component.get("id", "component"))
    material_name = component.get("material")

    if component_shape(component) == "cylinder":
        add_cylinder(name, scale, material_name, (x, y, z), rotate_x="shaft" in name.lower())
    else:
        add_box(name, scale, material_name, (x, y, z))

    children = component.get("children") or []
    for child_index, child in enumerate(children):
        add_component(child, child_index, len(children), parent_x=x, z=z + 0.16)


def add_labels_as_custom_properties(blueprint: dict) -> None:
    for obj in bpy.context.scene.objects:
        obj["eureka_object_id"] = blueprint.get("id")
        obj["eureka_source_query"] = blueprint.get("sourceQuery", "")


def setup_camera() -> None:
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 3))
    light = bpy.context.object
    light.name = "Key Light"
    light.data.energy = 450
    light.data.size = 5

    bpy.ops.object.camera_add(location=(0.0, -2.0, 1.2), rotation=(math.radians(60), 0, 0))
    bpy.context.scene.camera = bpy.context.object


def export_glb(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_texcoords=False,
        export_normals=True,
        export_materials="EXPORT",
        export_yup=True,
    )


def main() -> None:
    blueprint_path, output_path = parse_args()
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))

    clear_scene()

    components = blueprint.get("components") or []
    for index, component in enumerate(components):
        add_component(component, index, len(components))

    add_labels_as_custom_properties(blueprint)
    setup_camera()
    export_glb(output_path)


if __name__ == "__main__":
    main()

