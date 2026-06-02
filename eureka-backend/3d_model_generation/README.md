# Eureka 3D Model Generation

This module defines the search-to-3D pipeline for real-world objects.
It is intentionally isolated from the running backend until it is wired into
the existing application.

## Goal

Given a user search such as `car engine`, `fighter jet`, `dog skeleton`, or
`human heart`, Eureka should create a real-scale 3D object blueprint and use it
to generate or update a low-GPU friendly 3D model.

## Pipeline

1. Parse the user search query.
2. Detect the object category and expected real-world scale.
3. Build an object blueprint with systems, components, functions, materials,
   and measurements.
4. Generate or update a procedural model from the blueprint.
5. Export a web-ready `glb` model.
6. Load details progressively with LOD and component streaming.

## Current Ready Version

This folder now includes a self-contained 3D object maker that can:

- accept a search query,
- detect a broad object category,
- create a real-scale component blueprint,
- generate a low-GPU procedural `.glb` model without Blender,
- expose the result through a small FastAPI service.
- generate a generic object for unknown searches instead of failing.

It does not replace the main Eureka backend yet. It is isolated so existing
project behavior stays unchanged.

## Run The API

Install dependencies in this folder:

```bash
pip install -r requirements.txt
```

Start the service:

```bash
python run_api.py
```

Or run with Docker:

```bash
docker compose up --build
```

Generate an object:

```bash
curl -X POST http://localhost:8093/api/3d/generate \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"car engine\",\"targetGpu\":\"low\"}"
```

You can search specific or unknown objects:

```text
car engine
fighter jet
dog skeleton
human heart
laptop cooling fan
ancient tower
solar flower
water pump
anything else
```

Known categories use stronger templates. Unknown searches use a generic
real-scale object blueprint with inferred components, so the maker still
returns a blueprint and `.glb` preview.

Response includes:

- `objectId`
- `blueprintUri`
- `modelUri`
- `realScale`
- `componentCount`

The generated files are written under:

```text
generated/
  blueprints/
  models/
```

For production deployment details, see `PRODUCTION.md`.

## Low GPU Rules

- Use `glb` as the primary web delivery format.
- Keep a low-poly outer model for first load.
- Load internal components only when the user zooms, expands, or isolates them.
- Generate separate LOD levels for large objects.
- Prefer instancing for repeated parts such as cells, bolts, blades, teeth,
  feathers, or screws.
- Keep metadata separate from mesh data so the viewer can show hierarchy before
  all geometry is loaded.

## High Quality Mesh Upgrade

The maker now has a two-stage model path:

1. Generate a fast procedural preview `.glb` immediately.
2. Create a mesh upgrade manifest for realistic component meshes.

Get the upgrade manifest:

```bash
curl http://localhost:8093/api/3d/mesh-upgrades/{objectId}
```

The manifest includes each component id, real scale, function, material, target
high-quality GLB URI, and a prompt for an AI, Blender, or artist pipeline.

Apply realistic mesh replacements:

```bash
curl -X POST http://localhost:8093/api/3d/mesh-upgrades/{objectId}/apply \
  -H "Content-Type: application/json" \
  -d "{\"replacements\":{\"engine_block\":\"/3d/generated/models/high_quality/car_engine/engine_block.glb\"}}"
```

This updates only component `modelUri` values. The hierarchy, component IDs,
real scale metadata, and low-poly preview stay stable.

## Blueprint Shape

The blueprint is stored as JSON. It should describe what the object is, how big
it is in real-world units, what parts it has, and what each part does.

See `object_blueprint.schema.json`.
