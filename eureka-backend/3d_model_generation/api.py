from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

try:
    from .mesh_upgrade import apply_mesh_replacements
except ImportError:
    from mesh_upgrade import apply_mesh_replacements

try:
    from .service import BLUEPRINT_ROOT, MODEL_ROOT, generate_object
except ImportError:
    from service import BLUEPRINT_ROOT, MODEL_ROOT, generate_object


class Generate3DRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=160)
    detailLevel: Literal["low", "medium", "high"] = "medium"
    realScale: bool = True
    includeInternalParts: bool = True
    targetGpu: Literal["low", "medium", "high"] = "low"
    highQuality: bool = True


class ApplyMeshReplacementRequest(BaseModel):
    replacements: dict[str, str] = Field(
        ...,
        description="Map component id to high-quality GLB URI.",
    )


app = FastAPI(title="Eureka 3D Object Maker", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eureka-3d-object-maker"}


@app.post("/api/3d/generate")
def generate_3d_object(request: Generate3DRequest) -> JSONResponse:
    result = generate_object(
        request.query,
        detail_level=request.detailLevel,
        high_quality=request.highQuality,
    )
    return JSONResponse(
        {
            "status": "complete",
            "qualityStatus": "preview_ready_high_quality_pending" if request.highQuality else "preview_ready",
            "objectId": result.object_id,
            "name": result.blueprint["name"],
            "category": result.blueprint["category"],
            "blueprintUri": f"/api/3d/blueprints/{result.object_id}",
            "modelUri": f"/api/3d/models/{result.object_id}.glb",
            "meshUpgradeUri": f"/api/3d/mesh-upgrades/{result.object_id}",
            "viewerModelUri": result.blueprint["model"]["uri"],
            "realScale": result.blueprint["realScale"],
            "componentCount": count_components(result.blueprint.get("components", [])),
        }
    )


@app.get("/api/3d/blueprints/{object_id}")
def get_blueprint(object_id: str) -> FileResponse:
    path = safe_file(BLUEPRINT_ROOT, object_id, ".json")
    return FileResponse(path, media_type="application/json")


@app.get("/api/3d/models/{object_id}.glb")
def get_model(object_id: str) -> FileResponse:
    path = safe_file(MODEL_ROOT, object_id, ".glb")
    return FileResponse(path, media_type="model/gltf-binary", filename=f"{object_id}.glb")


@app.get("/api/3d/mesh-upgrades/{object_id}")
def get_mesh_upgrade_manifest(object_id: str) -> FileResponse:
    root = MODEL_ROOT.parent / "mesh_upgrades"
    path = safe_file(root, object_id, ".mesh_upgrade.json")
    return FileResponse(path, media_type="application/json")


@app.post("/api/3d/mesh-upgrades/{object_id}/apply")
def apply_mesh_upgrade(object_id: str, request: ApplyMeshReplacementRequest) -> JSONResponse:
    blueprint_path = safe_file(BLUEPRINT_ROOT, object_id, ".json")
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    updated = apply_mesh_replacements(blueprint, request.replacements)
    blueprint_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return JSONResponse(
        {
            "status": "updated",
            "objectId": object_id,
            "blueprintUri": f"/api/3d/blueprints/{object_id}",
            "replacedComponents": sorted(request.replacements.keys()),
        }
    )


def safe_file(root: Path, object_id: str, suffix: str) -> Path:
    if not object_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid object id")
    path = (root / f"{object_id}{suffix}").resolve()
    if root.resolve() not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid object path")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Object not found")
    return path


def count_components(components: list[dict]) -> int:
    total = 0
    for component in components:
        total += 1
        total += count_components(component.get("children") or [])
    return total
