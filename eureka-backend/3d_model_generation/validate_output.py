from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


def validate_blueprint(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ["id", "name", "category", "realScale", "components"]:
        if key not in data:
            errors.append(f"blueprint missing {key}")
    if not isinstance(data.get("components"), list) or not data.get("components"):
        errors.append("blueprint must include at least one component")
    return errors


def validate_glb(path: Path) -> list[str]:
    errors: list[str] = []
    data = path.read_bytes()
    if len(data) < 20:
        return ["glb file is too small"]
    magic, version, total_length = struct.unpack("<4sII", data[:12])
    if magic != b"glTF":
        errors.append("glb magic header is invalid")
    if version != 2:
        errors.append("glb version must be 2")
    if total_length != len(data):
        errors.append("glb declared length does not match file size")
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python validate_output.py <blueprint.json> <model.glb>")
        return 2

    blueprint_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    errors = []
    errors.extend(validate_blueprint(blueprint_path))
    errors.extend(validate_glb(model_path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK: blueprint and GLB look valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

