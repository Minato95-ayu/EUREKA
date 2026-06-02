from __future__ import annotations

import base64
import json
import math
import struct
from pathlib import Path
from typing import Any


UNIT_TO_METERS = {
    "um": 0.000001,
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
}


def pad4(data: bytes, pad_byte: bytes = b" ") -> bytes:
    remainder = len(data) % 4
    if remainder == 0:
        return data
    return data + pad_byte * (4 - remainder)


def pack_floats(values: list[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def pack_uint16(values: list[int]) -> bytes:
    return struct.pack(f"<{len(values)}H", *values)


def meters(value: Any, unit: str, fallback: float) -> float:
    if value is None:
        return fallback
    return max(float(value) * UNIT_TO_METERS.get(unit, 1.0), 0.02)


def component_dimensions(component: dict[str, Any]) -> tuple[float, float, float]:
    scale = component.get("realScale") or {}
    unit = scale.get("unit", "cm")
    diameter = scale.get("diameter")
    length = meters(scale.get("length") or diameter, unit, 0.2)
    width = meters(scale.get("width") or diameter, unit, 0.16)
    height = meters(scale.get("height") or diameter, unit, 0.12)
    return length, width, height


def flatten_components(components: list[dict[str, Any]], level: int = 0) -> list[tuple[dict[str, Any], int]]:
    flat: list[tuple[dict[str, Any], int]] = []
    for component in components:
        flat.append((component, level))
        flat.extend(flatten_components(component.get("children") or [], level + 1))
    return flat


def material_color(component: dict[str, Any]) -> list[float]:
    material = str(component.get("material", "")).lower()
    if "steel" in material:
        return [0.48, 0.52, 0.56, 1.0]
    if "aluminum" in material:
        return [0.72, 0.74, 0.76, 1.0]
    if "iron" in material:
        return [0.28, 0.29, 0.30, 1.0]
    if "rubber" in material:
        return [0.02, 0.02, 0.02, 1.0]
    if "bone" in material:
        return [0.88, 0.84, 0.72, 1.0]
    if "muscle" in material or "cardiac" in material:
        return [0.68, 0.18, 0.22, 1.0]
    if "tissue" in material:
        return [0.76, 0.36, 0.40, 1.0]
    return [0.30, 0.50, 0.72, 1.0]


def write_blueprint_glb(blueprint: dict[str, Any], output_path: Path) -> None:
    positions = [
        -0.5, -0.5, -0.5,
        0.5, -0.5, -0.5,
        0.5, 0.5, -0.5,
        -0.5, 0.5, -0.5,
        -0.5, -0.5, 0.5,
        0.5, -0.5, 0.5,
        0.5, 0.5, 0.5,
        -0.5, 0.5, 0.5,
    ]
    normals = [
        -0.577, -0.577, -0.577,
        0.577, -0.577, -0.577,
        0.577, 0.577, -0.577,
        -0.577, 0.577, -0.577,
        -0.577, -0.577, 0.577,
        0.577, -0.577, 0.577,
        0.577, 0.577, 0.577,
        -0.577, 0.577, 0.577,
    ]
    indices = [
        0, 1, 2, 0, 2, 3,
        4, 6, 5, 4, 7, 6,
        0, 4, 5, 0, 5, 1,
        1, 5, 6, 1, 6, 2,
        2, 6, 7, 2, 7, 3,
        3, 7, 4, 3, 4, 0,
    ]

    position_bytes = pack_floats(positions)
    normal_bytes = pack_floats(normals)
    index_bytes = pack_uint16(indices)
    binary = pad4(position_bytes + normal_bytes + index_bytes, b"\x00")

    position_view_offset = 0
    normal_view_offset = len(position_bytes)
    index_view_offset = len(position_bytes) + len(normal_bytes)

    flat_components = flatten_components(blueprint.get("components") or [])
    nodes = []
    child_indices = []
    materials = []

    count = max(len(flat_components), 1)
    radius = max(count * 0.18, 0.5)
    for index, (component, level) in enumerate(flat_components):
        angle = (index / count) * math.tau
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        z = level * 0.22
        dimensions = component_dimensions(component)
        material_index = len(materials)
        materials.append({
            "name": component.get("material", "Generated Material"),
            "pbrMetallicRoughness": {
                "baseColorFactor": material_color(component),
                "metallicFactor": 0.15,
                "roughnessFactor": 0.75,
            },
        })
        mesh_index = len(child_indices)
        child_indices.append(len(nodes) + 1)
        nodes.append({
            "name": component.get("name", component.get("id", "Component")),
            "mesh": mesh_index,
            "translation": [x, y, z],
            "scale": list(dimensions),
            "extras": {
                "id": component.get("id"),
                "function": component.get("function"),
                "material": component.get("material"),
                "realScale": component.get("realScale"),
            },
        })

    meshes = [
        {
            "name": node["name"],
            "primitives": [
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1},
                    "indices": 2,
                    "material": index,
                }
            ],
        }
        for index, node in enumerate(nodes)
    ]

    root_node = {
        "name": blueprint.get("name", "Generated Object"),
        "children": list(range(1, len(nodes) + 1)),
        "extras": {
            "id": blueprint.get("id"),
            "category": blueprint.get("category"),
            "sourceQuery": blueprint.get("sourceQuery"),
            "realScale": blueprint.get("realScale"),
        },
    }
    all_nodes = [root_node] + nodes

    gltf = {
        "asset": {"version": "2.0", "generator": "Eureka Simple GLB Writer"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": all_nodes,
        "meshes": meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": position_view_offset, "byteLength": len(position_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": normal_view_offset, "byteLength": len(normal_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": index_view_offset, "byteLength": len(index_bytes), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
            {"bufferView": 1, "componentType": 5126, "count": 8, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": len(indices), "type": "SCALAR", "min": [0], "max": [7]},
        ],
        "extras": {
            "blueprintPreview": {
                "id": blueprint.get("id"),
                "name": blueprint.get("name"),
                "category": blueprint.get("category"),
            }
        },
    }

    json_chunk = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = pad4(binary, b"\x00")
    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file:
        file.write(struct.pack("<4sII", b"glTF", 2, total_length))
        file.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        file.write(json_chunk)
        file.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00"))
        file.write(bin_chunk)

    encoded_blueprint = base64.b64encode(json.dumps(blueprint).encode("utf-8")).decode("ascii")
    sidecar = output_path.with_suffix(".blueprint.b64.txt")
    sidecar.write_text(encoded_blueprint, encoding="ascii")

