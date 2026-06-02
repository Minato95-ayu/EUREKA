from __future__ import annotations

import json
from pathlib import Path
from typing import Any


UPGRADE_ROOT_NAME = "mesh_upgrades"


def flatten_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for component in components:
        flat.append(component)
        flat.extend(flatten_components(component.get("children") or []))
    return flat


def prompt_for_component(object_name: str, component: dict[str, Any]) -> str:
    scale = component.get("realScale") or {}
    material = component.get("material", "context accurate material")
    function = component.get("function", "performs its real-world function")
    scale_text = ", ".join(f"{key}: {value}" for key, value in scale.items())
    return (
        f"Create a production-ready realistic GLB mesh for '{component.get('name')}' "
        f"inside '{object_name}'. Use real-world proportions ({scale_text}), "
        f"material: {material}. The part function is: {function}. "
        "Keep topology clean, use separate named submeshes for important details, "
        "keep pivot centered, use meters as export scale, and optimize for web viewing."
    )


def build_mesh_upgrade_manifest(blueprint: dict[str, Any], output_root: Path) -> Path:
    object_id = blueprint["id"]
    object_name = blueprint.get("name", object_id)
    upgrade_root = output_root / UPGRADE_ROOT_NAME
    upgrade_root.mkdir(parents=True, exist_ok=True)

    components = flatten_components(blueprint.get("components") or [])
    parts = []
    for component in components:
        component_id = component.get("id", "component")
        high_quality_uri = f"/3d/generated/models/high_quality/{object_id}/{component_id}.glb"
        parts.append(
            {
                "componentId": component_id,
                "componentName": component.get("name", component_id),
                "currentPreview": "procedural",
                "targetUri": high_quality_uri,
                "status": "needs_high_quality_mesh",
                "replacementMode": "replace_component_model_uri",
                "prompt": prompt_for_component(object_name, component),
                "realScale": component.get("realScale"),
                "material": component.get("material"),
                "function": component.get("function"),
            }
        )

    manifest = {
        "objectId": object_id,
        "objectName": object_name,
        "sourceQuery": blueprint.get("sourceQuery"),
        "status": "preview_ready_high_quality_pending",
        "previewModelUri": blueprint.get("model", {}).get("uri"),
        "strategy": [
            "Use procedural GLB immediately for viewer preview.",
            "Generate or import high-quality GLB per component.",
            "Validate scale and pivot.",
            "Replace component modelUri in blueprint without changing component IDs.",
            "Keep low-poly preview as LOD0 fallback.",
        ],
        "parts": parts,
    }

    manifest_path = upgrade_root / f"{object_id}.mesh_upgrade.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def apply_mesh_replacements(blueprint: dict[str, Any], replacement_map: dict[str, str]) -> dict[str, Any]:
    updated = json.loads(json.dumps(blueprint))

    def apply_to_components(components: list[dict[str, Any]]) -> None:
        for component in components:
            component_id = component.get("id")
            if component_id in replacement_map:
                component["modelUri"] = replacement_map[component_id]
            apply_to_components(component.get("children") or [])

    apply_to_components(updated.get("components") or [])
    return updated

