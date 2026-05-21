import json
from pathlib import Path

from app.models.object_graph import ExplorableObject, ObjectComponent, ObjectSearchResult


class ObjectLibrary:
    """Loads curated demo objects for the first search-to-3D MVP."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).resolve().parents[1] / "data" / "demo_objects"
        self._objects: dict[str, ExplorableObject] = {}
        self._load_objects()

    def _load_objects(self) -> None:
        self._objects.clear()
        if not self.data_dir.exists():
            return

        for path in self.data_dir.glob("*.json"):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            obj = ExplorableObject.model_validate(payload)
            self._objects[obj.id] = obj

    def search(self, query: str) -> list[ObjectSearchResult]:
        normalized = query.strip().lower()
        objects = list(self._objects.values())

        if normalized:
            objects = [
                obj
                for obj in objects
                if normalized in obj.name.lower()
                or normalized in obj.type.lower()
                or normalized in obj.summary.lower()
                or any(normalized in component.name.lower() for component in obj.components)
            ]

        return [
            ObjectSearchResult(
                id=obj.id,
                name=obj.name,
                type=obj.type,
                summary=obj.summary,
                componentCount=len(obj.components),
            )
            for obj in objects
        ]

    def get_object(self, object_id: str) -> ExplorableObject | None:
        return self._objects.get(object_id)

    def get_component(self, object_id: str, component_id: str) -> ObjectComponent | None:
        obj = self.get_object(object_id)
        if not obj:
            return None
        return next((component for component in obj.components if component.id == component_id), None)

