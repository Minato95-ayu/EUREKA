from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .config import settings
except ImportError:
    from config import settings

try:
    from .mesh_upgrade import build_mesh_upgrade_manifest
except ImportError:
    from mesh_upgrade import build_mesh_upgrade_manifest

try:
    from .simple_glb_writer import write_blueprint_glb
except ImportError:
    from simple_glb_writer import write_blueprint_glb


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = settings.output_root
BLUEPRINT_ROOT = OUTPUT_ROOT / "blueprints"
MODEL_ROOT = OUTPUT_ROOT / "models"


@dataclass(frozen=True)
class GenerationResult:
    object_id: str
    blueprint_path: Path
    model_path: Path
    mesh_upgrade_path: Path
    blueprint: dict[str, Any]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "object"


def make_component(
    component_id: str,
    name: str,
    function: str,
    material: str,
    scale: dict[str, Any],
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    component: dict[str, Any] = {
        "id": component_id,
        "name": name,
        "function": function,
        "material": material,
        "realScale": scale,
    }
    if children:
        component["children"] = children
    return component


def detect_category(query: str) -> str:
    q = query.lower()
    if any(word in q for word in ["car", "bike", "motorcycle", "truck", "engine"]):
        return "vehicle"
    if any(word in q for word in ["plane", "jet", "aircraft", "helicopter"]):
        return "aircraft"
    if any(word in q for word in ["dog", "bird", "cat", "animal"]):
        return "animal"
    if any(word in q for word in ["human", "heart", "body", "organ", "brain"]):
        return "human_body"
    if any(word in q for word in ["robot", "machine", "motor", "pump", "turbine"]):
        return "machine"
    if any(word in q for word in ["tree", "flower", "plant", "leaf", "root"]):
        return "plant"
    if any(word in q for word in ["house", "building", "bridge", "tower", "room"]):
        return "structure"
    if any(word in q for word in ["phone", "laptop", "camera", "watch", "speaker"]):
        return "device"
    return "generic_object"


def vehicle_blueprint(query: str, object_id: str) -> dict[str, Any]:
    name = "Inline 4 Cylinder Car Engine" if "engine" in query.lower() else "Generic Vehicle"
    components = [
        make_component(
            "engine_block",
            "Engine Block",
            "Holds cylinders and supports the rotating assembly.",
            "Cast aluminum",
            {"unit": "cm", "length": 48, "width": 32, "height": 34},
            [
                make_component(
                    f"cylinder_{index}",
                    f"Cylinder {index}",
                    "Guides piston movement through the combustion cycle.",
                    "Honed metal bore",
                    {"unit": "cm", "diameter": 8, "height": 9},
                )
                for index in range(1, 5)
            ],
        ),
        make_component(
            "crankshaft",
            "Crankshaft",
            "Converts piston motion into rotation.",
            "Forged steel",
            {"unit": "cm", "length": 42, "diameter": 7},
        ),
        make_component(
            "intake_manifold",
            "Intake Manifold",
            "Distributes incoming air to the cylinders.",
            "Aluminum or composite",
            {"unit": "cm", "length": 44, "width": 16, "height": 18},
        ),
        make_component(
            "exhaust_manifold",
            "Exhaust Manifold",
            "Routes exhaust gases away from cylinders.",
            "Stainless steel",
            {"unit": "cm", "length": 46, "width": 14, "height": 16},
        ),
    ]
    return blueprint(object_id, name, "vehicle", query, {"unit": "cm", "length": 60, "width": 45, "height": 55, "massKg": 140}, components)


def aircraft_blueprint(query: str, object_id: str) -> dict[str, Any]:
    components = [
        make_component("fuselage", "Fuselage", "Main body that carries payload and connects flight surfaces.", "Aluminum alloy", {"unit": "m", "length": 18, "width": 2.6, "height": 3}),
        make_component("left_wing", "Left Wing", "Creates lift and stores fuel in many aircraft.", "Composite and aluminum", {"unit": "m", "length": 8, "width": 2.2, "height": 0.25}),
        make_component("right_wing", "Right Wing", "Creates lift and stabilizes roll with control surfaces.", "Composite and aluminum", {"unit": "m", "length": 8, "width": 2.2, "height": 0.25}),
        make_component("jet_engine", "Jet Engine", "Compresses air, burns fuel, and accelerates exhaust for thrust.", "Titanium and nickel alloy", {"unit": "m", "length": 3.2, "diameter": 1.4}),
        make_component("landing_gear", "Landing Gear", "Supports taxi, takeoff, and landing loads.", "Steel and rubber", {"unit": "m", "length": 2.5, "width": 1.6, "height": 1.2}),
    ]
    return blueprint(object_id, "Aircraft", "aircraft", query, {"unit": "m", "length": 18, "width": 16, "height": 4.5, "massKg": 7000}, components)


def animal_blueprint(query: str, object_id: str) -> dict[str, Any]:
    animal_name = "Bird" if "bird" in query.lower() else "Dog" if "dog" in query.lower() else "Animal"
    components = [
        make_component("skeleton", "Skeletal System", "Supports body shape and protects internal organs.", "Bone", {"unit": "cm", "length": 70, "width": 20, "height": 35}),
        make_component("muscular_system", "Muscular System", "Produces movement and posture control.", "Muscle tissue", {"unit": "cm", "length": 72, "width": 22, "height": 36}),
        make_component("heart", "Heart", "Pumps blood through the circulatory system.", "Cardiac muscle", {"unit": "cm", "length": 8, "width": 6, "height": 6}),
        make_component("lungs", "Lungs", "Exchange oxygen and carbon dioxide.", "Soft tissue", {"unit": "cm", "length": 12, "width": 8, "height": 7}),
        make_component("nervous_system", "Nervous System", "Coordinates sensing, movement, and body regulation.", "Neural tissue", {"unit": "cm", "length": 65, "width": 8, "height": 8}),
    ]
    return blueprint(object_id, animal_name, "animal", query, {"unit": "cm", "length": 75, "width": 25, "height": 45, "massKg": 22}, components)


def human_blueprint(query: str, object_id: str) -> dict[str, Any]:
    organ_focus = "heart" in query.lower()
    if organ_focus:
        components = [
            make_component("left_ventricle", "Left Ventricle", "Pumps oxygenated blood to the body.", "Cardiac muscle", {"unit": "cm", "length": 7, "width": 4, "height": 5}),
            make_component("right_ventricle", "Right Ventricle", "Pumps deoxygenated blood to the lungs.", "Cardiac muscle", {"unit": "cm", "length": 6, "width": 4, "height": 5}),
            make_component("left_atrium", "Left Atrium", "Receives oxygenated blood from pulmonary veins.", "Cardiac muscle", {"unit": "cm", "length": 4, "width": 3, "height": 3}),
            make_component("right_atrium", "Right Atrium", "Receives deoxygenated blood from the body.", "Cardiac muscle", {"unit": "cm", "length": 4, "width": 3, "height": 3}),
        ]
        return blueprint(object_id, "Human Heart", "human_body", query, {"unit": "cm", "length": 12, "width": 8, "height": 6, "massKg": 0.3}, components)

    components = [
        make_component("skeletal_system", "Skeletal System", "Supports the body and protects organs.", "Bone", {"unit": "cm", "height": 170, "width": 45, "length": 30}),
        make_component("muscular_system", "Muscular System", "Creates movement and maintains posture.", "Muscle tissue", {"unit": "cm", "height": 168, "width": 48, "length": 32}),
        make_component("circulatory_system", "Circulatory System", "Moves blood, oxygen, nutrients, and waste.", "Blood vessels and cardiac tissue", {"unit": "cm", "height": 165, "width": 42, "length": 28}),
        make_component("nervous_system", "Nervous System", "Controls sensing, movement, and body regulation.", "Neural tissue", {"unit": "cm", "height": 160, "width": 18, "length": 16}),
    ]
    return blueprint(object_id, "Human Body", "human_body", query, {"unit": "cm", "height": 170, "width": 50, "length": 30, "massKg": 70}, components)


def generic_blueprint(query: str, object_id: str) -> dict[str, Any]:
    category = detect_category(query)
    real_scale = estimate_real_scale(query, category)
    components = infer_components(query, category, real_scale)
    return blueprint(object_id, title_from_query(query), category, query, real_scale, components)


def title_from_query(query: str) -> str:
    return " ".join(word.capitalize() for word in query.split()) or "Generated Object"


def stable_number(query: str, minimum: int, maximum: int) -> int:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16)
    return minimum + value % (maximum - minimum + 1)


def estimate_real_scale(query: str, category: str) -> dict[str, Any]:
    q = query.lower()
    if category == "structure":
        return {"unit": "m", "length": stable_number(q, 6, 40), "width": stable_number(q + "w", 4, 18), "height": stable_number(q + "h", 3, 80)}
    if category == "plant":
        return {"unit": "cm", "height": stable_number(q, 20, 800), "width": stable_number(q + "w", 8, 300), "length": stable_number(q + "l", 8, 300)}
    if category == "device":
        return {"unit": "cm", "length": stable_number(q, 8, 45), "width": stable_number(q + "w", 4, 30), "height": stable_number(q + "h", 1, 18)}
    if category == "machine":
        return {"unit": "cm", "length": stable_number(q, 30, 220), "width": stable_number(q + "w", 20, 120), "height": stable_number(q + "h", 20, 160)}
    if "tiny" in q or "small" in q:
        return {"unit": "cm", "length": 12, "width": 8, "height": 6}
    if "large" in q or "big" in q or "giant" in q:
        return {"unit": "m", "length": 4, "width": 2, "height": 2}
    return {"unit": "cm", "length": stable_number(q, 25, 120), "width": stable_number(q + "w", 12, 80), "height": stable_number(q + "h", 8, 70)}


def scaled(real_scale: dict[str, Any], length_ratio: float, width_ratio: float, height_ratio: float) -> dict[str, Any]:
    return {
        "unit": real_scale.get("unit", "cm"),
        "length": round(float(real_scale.get("length", real_scale.get("width", 40))) * length_ratio, 3),
        "width": round(float(real_scale.get("width", real_scale.get("length", 25))) * width_ratio, 3),
        "height": round(float(real_scale.get("height", real_scale.get("width", 20))) * height_ratio, 3),
    }


def infer_components(query: str, category: str, real_scale: dict[str, Any]) -> list[dict[str, Any]]:
    q = query.lower()
    if category == "device":
        return [
            make_component("outer_case", "Outer Case", "Protects the device and defines its external form.", "Aluminum or polymer", scaled(real_scale, 1.0, 1.0, 0.45)),
            make_component("display_or_interface", "Display or Interface", "Allows the user to view information or control the object.", "Glass and electronics", scaled(real_scale, 0.82, 0.72, 0.05)),
            make_component("main_board", "Main Board", "Connects processing, power, sensors, and input systems.", "Printed circuit board", scaled(real_scale, 0.72, 0.58, 0.06)),
            make_component("power_unit", "Power Unit", "Stores or regulates energy for operation.", "Battery and power electronics", scaled(real_scale, 0.42, 0.34, 0.1)),
        ]
    if category == "plant":
        return [
            make_component("root_system", "Root System", "Anchors the plant and absorbs water and minerals.", "Plant tissue", scaled(real_scale, 0.42, 0.42, 0.18)),
            make_component("stem_or_trunk", "Stem or Trunk", "Supports the body and transports fluids.", "Plant fiber", scaled(real_scale, 0.16, 0.16, 0.85)),
            make_component("leaf_system", "Leaf System", "Captures light and exchanges gases.", "Leaf tissue", scaled(real_scale, 0.9, 0.55, 0.08)),
            make_component("reproductive_parts", "Flower or Seed Parts", "Supports reproduction when present.", "Plant tissue", scaled(real_scale, 0.28, 0.28, 0.18)),
        ]
    if category == "structure":
        return [
            make_component("foundation", "Foundation", "Transfers object load into the ground or base.", "Concrete or stone", scaled(real_scale, 1.0, 1.0, 0.12)),
            make_component("frame", "Structural Frame", "Carries major loads and preserves shape.", "Steel, wood, or concrete", scaled(real_scale, 0.92, 0.92, 0.85)),
            make_component("outer_surface", "Outer Surface", "Protects the structure from environment.", "Composite building material", scaled(real_scale, 1.0, 1.0, 0.35)),
            make_component("internal_space", "Internal Space", "Represents usable interior volume and partitions.", "Mixed material", scaled(real_scale, 0.78, 0.78, 0.72)),
        ]
    if category == "machine":
        return [
            make_component("housing", "Housing", "Protects moving and powered parts.", "Cast metal or polymer", scaled(real_scale, 1.0, 0.82, 0.75)),
            make_component("drive_core", "Drive Core", "Creates or transfers mechanical power.", "Steel and copper", scaled(real_scale, 0.52, 0.45, 0.42)),
            make_component("control_unit", "Control Unit", "Coordinates operation and safety behavior.", "Electronics", scaled(real_scale, 0.28, 0.22, 0.16)),
            make_component("connector_system", "Connector System", "Moves force, fluid, signal, or power between parts.", "Metal and composite", scaled(real_scale, 0.62, 0.18, 0.18)),
        ]

    tokens = [token for token in re.split(r"[^a-z0-9]+", q) if token and token not in {"a", "an", "the", "of", "with", "for"}]
    focus = " ".join(tokens[:3]) or "object"
    components = [
        make_component("outer_body", "Outer Body", f"Defines the visible form of the {focus}.", "Mixed material", scaled(real_scale, 1.0, 0.9, 0.82)),
        make_component("primary_core", "Primary Core", f"Represents the main functional mass of the {focus}.", "Dense internal material", scaled(real_scale, 0.58, 0.48, 0.45)),
        make_component("support_structure", "Support Structure", "Maintains alignment, shape, and load paths.", "Structural material", scaled(real_scale, 0.72, 0.24, 0.24)),
        make_component("surface_detail_set", "Surface Detail Set", "Provides visible smaller features inferred from the search query.", "Surface material", scaled(real_scale, 0.32, 0.18, 0.12)),
    ]
    if len(tokens) > 1:
        components.append(
            make_component(
                f"{slugify(tokens[-1])}_feature",
                f"{tokens[-1].capitalize()} Feature",
                f"Search-specific feature inferred from '{query}'.",
                "Context dependent material",
                scaled(real_scale, 0.22, 0.16, 0.14),
            )
        )
    return components


def blueprint(
    object_id: str,
    name: str,
    category: str,
    query: str,
    real_scale: dict[str, Any],
    components: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": object_id,
        "name": name,
        "category": category,
        "sourceQuery": query,
        "realScale": real_scale,
        "model": {
            "format": "glb",
            "uri": f"/3d/generated/models/{object_id}.glb",
            "lod": [
                {"level": 0, "uri": f"/3d/generated/models/{object_id}.glb", "maxScreenSize": 0.65}
            ],
        },
        "components": components,
    }


def build_blueprint(query: str) -> dict[str, Any]:
    object_id = f"{slugify(query)}_{uuid.uuid4().hex[:8]}"
    category = detect_category(query)
    if category == "vehicle":
        return vehicle_blueprint(query, object_id)
    if category == "aircraft":
        return aircraft_blueprint(query, object_id)
    if category == "animal":
        return animal_blueprint(query, object_id)
    if category == "human_body":
        return human_blueprint(query, object_id)
    return generic_blueprint(query, object_id)


def generate_object(query: str, detail_level: str = "medium", high_quality: bool = True) -> GenerationResult:
    BLUEPRINT_ROOT.mkdir(parents=True, exist_ok=True)
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)

    generated = build_blueprint(query)
    object_id = generated["id"]
    blueprint_path = BLUEPRINT_ROOT / f"{object_id}.json"
    model_path = MODEL_ROOT / f"{object_id}.glb"

    blueprint_path.write_text(json.dumps(generated, indent=2), encoding="utf-8")
    write_blueprint_glb(generated, model_path)
    mesh_upgrade_path = build_mesh_upgrade_manifest(generated, OUTPUT_ROOT) if high_quality else OUTPUT_ROOT / "mesh_upgrades" / f"{object_id}.mesh_upgrade.json"

    return GenerationResult(
        object_id=object_id,
        blueprint_path=blueprint_path,
        model_path=model_path,
        mesh_upgrade_path=mesh_upgrade_path,
        blueprint=generated,
    )
