import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from app.models.object_graph import ExplorableObject, ObjectComponent, ObjectModelRef

class ObjectRepository:
    """
    Manages the persistence of declarative CAD graphs (source of truth)
    and compiled artifacts under app/data/object_library/{object_id}/
    """

    def __init__(self, library_dir: Path | None = None):
        # Resolve path relative to backend root
        base_dir = Path(__file__).resolve().parents[1]
        self.library_dir = library_dir or base_dir / "data" / "object_library"
        self.library_dir.mkdir(parents=True, exist_ok=True)

    def get_object_dir(self, object_id: str) -> Path:
        """Returns the directory path for a given object ID."""
        return self.library_dir / object_id

    def save_object(self, obj: ExplorableObject, compiled_glb_path: str | None = None) -> None:
        """
        Decomposes and saves the ExplorableObject into:
        semantic.json, hierarchy.json, constraints.json, parameters.json, metadata.json, and compiled.glb
        """
        obj_dir = self.get_object_dir(obj.id)
        obj_dir.mkdir(parents=True, exist_ok=True)

        semantic_components = []
        constraints = []
        hierarchy_relations = []

        for comp in obj.components:
            comp_dict = comp.model_dump(by_alias=True)
            
            # Extract layout to constraints.json
            layout = comp_dict.pop("layout", None)
            if layout:
                constraints.append({
                    "id": comp.id,
                    "layout": layout
                })
                
            semantic_components.append(comp_dict)
            
            hierarchy_relations.append({
                "id": comp.id,
                "parentId": comp.parent_id,
                "children": comp.children
            })

        # Save semantic.json
        with open(obj_dir / "semantic.json", "w", encoding="utf-8") as f:
            json.dump(semantic_components, f, indent=2)

        # Save hierarchy.json
        with open(obj_dir / "hierarchy.json", "w", encoding="utf-8") as f:
            json.dump({
                "rootId": next((c.id for c in obj.components if c.parent_id is None), None),
                "relations": hierarchy_relations
            }, f, indent=2)

        # Save constraints.json
        with open(obj_dir / "constraints.json", "w", encoding="utf-8") as f:
            json.dump(constraints, f, indent=2)

        # Save parameters.json
        with open(obj_dir / "parameters.json", "w", encoding="utf-8") as f:
            json.dump(obj.parameters, f, indent=2)

        # Save metadata.json
        with open(obj_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "id": obj.id,
                "name": obj.name,
                "type": obj.type,
                "summary": obj.summary,
                "defaultView": obj.default_view
            }, f, indent=2)

        # Copy final compiled glb to the library folder
        if compiled_glb_path and os.path.exists(compiled_glb_path):
            shutil.copy2(compiled_glb_path, obj_dir / "compiled.glb")

    def load_object(self, object_id: str) -> ExplorableObject | None:
        """
        Loads and reconstructs the ExplorableObject model from the persistent library.
        """
        obj_dir = self.get_object_dir(object_id)
        if not obj_dir.exists():
            return None

        try:
            # Load metadata
            with open(obj_dir / "metadata.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
                
            # Load parameters
            parameters = {}
            if (obj_dir / "parameters.json").exists():
                with open(obj_dir / "parameters.json", "r", encoding="utf-8") as f:
                    parameters = json.load(f)

            # Load constraints (layouts)
            layouts_dict = {}
            if (obj_dir / "constraints.json").exists():
                with open(obj_dir / "constraints.json", "r", encoding="utf-8") as f:
                    constraints = json.load(f)
                    for c in constraints:
                        layouts_dict[c["id"]] = c.get("layout")

            # Load semantic components
            with open(obj_dir / "semantic.json", "r", encoding="utf-8") as f:
                semantic_comps = json.load(f)

            components = []
            for comp_data in semantic_comps:
                cid = comp_data.get("id")
                # Merge layout back into component
                if cid in layouts_dict:
                    comp_data["layout"] = layouts_dict[cid]
                components.append(ObjectComponent.model_validate(comp_data))

            # Asset path reference (if compiled.glb exists)
            has_glb = (obj_dir / "compiled.glb").exists()
            asset_url = f"/api/objects/download/{object_id}.glb" if has_glb else None
            model_kind = "gltf" if has_glb else "procedural"
            
            return ExplorableObject(
                id=meta["id"],
                name=meta["name"],
                type=meta["type"],
                summary=meta["summary"],
                defaultView=meta.get("defaultView", "assembled"),
                model=ObjectModelRef(kind=model_kind, assetUrl=asset_url),
                components=components,
                parameters=parameters
            )
        except Exception:
            return None
