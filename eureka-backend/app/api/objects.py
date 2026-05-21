from fastapi import APIRouter, HTTPException, Query

from app.models.object_graph import ExplorableObject, ObjectComponent, ObjectSearchResult
from app.services.object_library import ObjectLibrary


router = APIRouter(prefix="/api/objects", tags=["objects"])
object_library = ObjectLibrary()


@router.get("/search", response_model=list[ObjectSearchResult])
async def search_objects(q: str = Query(default="", description="Object or component search text")):
    return object_library.search(q)


@router.get("/{object_id}", response_model=ExplorableObject)
async def get_object(object_id: str):
    obj = object_library.get_object(object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


@router.get("/{object_id}/components/{component_id}", response_model=ObjectComponent)
async def get_component(object_id: str, component_id: str):
    component = object_library.get_component(object_id, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component

