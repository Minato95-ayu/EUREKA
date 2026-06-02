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

## Low GPU Rules

- Use `glb` as the primary web delivery format.
- Keep a low-poly outer model for first load.
- Load internal components only when the user zooms, expands, or isolates them.
- Generate separate LOD levels for large objects.
- Prefer instancing for repeated parts such as cells, bolts, blades, teeth,
  feathers, or screws.
- Keep metadata separate from mesh data so the viewer can show hierarchy before
  all geometry is loaded.

## Blueprint Shape

The blueprint is stored as JSON. It should describe what the object is, how big
it is in real-world units, what parts it has, and what each part does.

See `object_blueprint.schema.json`.

