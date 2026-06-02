from __future__ import annotations

from service import generate_object


if __name__ == "__main__":
    result = generate_object("car engine", detail_level="high", high_quality=True)
    print(f"objectId={result.object_id}")
    print(f"blueprint={result.blueprint_path}")
    print(f"model={result.model_path}")
    print(f"meshUpgrade={result.mesh_upgrade_path}")

