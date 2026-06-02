from __future__ import annotations

import json
import logging
import time
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

try:
    from .config import settings
except ImportError:
    from config import settings

try:
    from .job_store import JobStore
except ImportError:
    from job_store import JobStore

try:
    from .mesh_upgrade import apply_mesh_replacements
except ImportError:
    from mesh_upgrade import apply_mesh_replacements

try:
    from .service import BLUEPRINT_ROOT, MODEL_ROOT, generate_object
except ImportError:
    from service import BLUEPRINT_ROOT, MODEL_ROOT, generate_object


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("eureka_3d_object_maker")
job_store = JobStore(settings.output_root / "jobs")


class Generate3DRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=settings.max_query_length)
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


app = FastAPI(title="Eureka 3D Object Maker", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info("%s %s %s %sms", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "status": "running",
        "docs": "/docs",
        "generate": "/api/3d/generate",
    }


@app.get("/ready")
def ready() -> dict[str, str]:
    settings.output_root.mkdir(parents=True, exist_ok=True)
    if not settings.output_root.exists():
        raise HTTPException(status_code=503, detail="Output root is unavailable")
    return {"status": "ready", "outputRoot": str(settings.output_root)}


@app.post("/api/3d/generate", dependencies=[Depends(require_api_key)])
def generate_3d_object(request: Generate3DRequest) -> JSONResponse:
    result = generate_object(
        request.query,
        detail_level=request.detailLevel,
        high_quality=request.highQuality,
    )
    return JSONResponse(build_generation_response(result, request.highQuality))


@app.post("/api/3d/jobs", dependencies=[Depends(require_api_key)])
def create_generation_job(request: Generate3DRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    job = job_store.create(
        request.query,
        {
            "detailLevel": request.detailLevel,
            "realScale": request.realScale,
            "includeInternalParts": request.includeInternalParts,
            "targetGpu": request.targetGpu,
            "highQuality": request.highQuality,
        },
    )
    background_tasks.add_task(run_generation_job, job["jobId"], request)
    return JSONResponse(
        status_code=202,
        content={
            "jobId": job["jobId"],
            "status": "queued",
            "statusUri": f"/api/3d/jobs/{job['jobId']}",
        },
    )


@app.get("/api/3d/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_generation_job(job_id: str) -> JSONResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@app.get("/api/3d/blueprints/{object_id}", dependencies=[Depends(require_api_key)])
def get_blueprint(object_id: str) -> FileResponse:
    path = safe_file(BLUEPRINT_ROOT, object_id, ".json")
    return FileResponse(path, media_type="application/json")


@app.get("/api/3d/models/{object_id}.glb", dependencies=[Depends(require_api_key)])
def get_model(object_id: str) -> FileResponse:
    path = safe_file(MODEL_ROOT, object_id, ".glb")
    return FileResponse(path, media_type="model/gltf-binary", filename=f"{object_id}.glb")


@app.get("/api/3d/mesh-upgrades/{object_id}", dependencies=[Depends(require_api_key)])
def get_mesh_upgrade_manifest(object_id: str) -> FileResponse:
    root = MODEL_ROOT.parent / "mesh_upgrades"
    path = safe_file(root, object_id, ".mesh_upgrade.json")
    return FileResponse(path, media_type="application/json")


@app.post("/api/3d/mesh-upgrades/{object_id}/apply", dependencies=[Depends(require_api_key)])
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


def build_generation_response(result, high_quality: bool) -> dict:
    return {
        "status": "complete",
        "qualityStatus": "preview_ready_high_quality_pending" if high_quality else "preview_ready",
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


def run_generation_job(job_id: str, request: Generate3DRequest) -> None:
    try:
        job_store.mark_running(job_id)
        result = generate_object(
            request.query,
            detail_level=request.detailLevel,
            high_quality=request.highQuality,
        )
        job_store.mark_complete(job_id, build_generation_response(result, request.highQuality))
    except Exception as exc:
        logger.exception("3D generation job failed: %s", job_id)
        job_store.mark_failed(job_id, str(exc))
