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

## Generation Notes

- The first version can generate simple procedural geometry from primitives.
- Later versions can replace primitive components with high quality generated
  or curated `glb` meshes.
- Existing 3D models should be updated by replacing component model URIs, not
  by changing the blueprint tree contract.

