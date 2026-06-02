# Search-to-3D Generation Contract

## Request

```json
{
  "query": "car engine",
  "detailLevel": "medium",
  "realScale": true,
  "includeInternalParts": true,
  "targetGpu": "low"
}
```

## Response

```json
{
  "jobId": "gen_123",
  "status": "queued",
  "blueprintUri": "/3d/blueprints/car_engine_inline_4_001.json",
  "previewModelUri": "/models/generated/car_engine_inline_4_001_lod0.glb"
}
```

## Job Result

```json
{
  "jobId": "gen_123",
  "status": "complete",
  "objectId": "car_engine_inline_4_001",
  "modelUri": "/models/generated/car_engine_inline_4_001.glb",
  "blueprintUri": "/3d/blueprints/car_engine_inline_4_001.json"
}
```

## Ready Endpoint

The first working API is synchronous and returns a completed object immediately:

```http
POST /api/3d/generate
```

```json
{
  "query": "fighter jet",
  "detailLevel": "medium",
  "realScale": true,
  "includeInternalParts": true,
  "targetGpu": "low"
}
```

It writes a blueprint JSON file and a procedural `.glb` file. The `.glb` uses
simple generated geometry so it works as a fast preview model before high
quality meshes are available.

## Generation Notes

- The first version can generate simple procedural geometry from primitives.
- Later versions can replace primitive components with high quality generated
  or curated `glb` meshes.
- Existing 3D models should be updated by replacing component model URIs, not
  by changing the blueprint tree contract.

## High Quality Mesh Upgrade

The generator also creates a mesh upgrade manifest:

```http
GET /api/3d/mesh-upgrades/{objectId}
```

Each manifest part includes:

```json
{
  "componentId": "engine_block",
  "targetUri": "/3d/generated/models/high_quality/object/engine_block.glb",
  "status": "needs_high_quality_mesh",
  "replacementMode": "replace_component_model_uri",
  "prompt": "Create a production-ready realistic GLB mesh..."
}
```

When the realistic mesh is ready, apply it:

```http
POST /api/3d/mesh-upgrades/{objectId}/apply
```

```json
{
  "replacements": {
    "engine_block": "/3d/generated/models/high_quality/object/engine_block.glb"
  }
}
```
