# 3D Generation Scripts

## `generate_glb_from_blueprint.py`

Creates a first-pass procedural `glb` model from an object blueprint.

Example:

```bash
blender --background --python generate_glb_from_blueprint.py -- \
  ../examples/car_engine.blueprint.json \
  ../../static/models/generated/car_engine_inline_4_001.glb
```

The current generator intentionally uses simple primitive geometry. This keeps
the first generated model low-GPU friendly and gives Eureka a stable component
tree before replacing parts with higher quality meshes.

