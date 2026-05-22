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


@router.post("/generate", response_model=ExplorableObject)
async def generate_object(q: str = Query(..., description="Object name to generate")):
    from main import ollama_service
    from app.agents.object_architect_agent import ObjectArchitectAgent
    
    if not ollama_service:
        # For testing fallback or direct CLI invocation where FastAPI startup hasn't run
        from app.services.ollama_service import OllamaService
        from app.config import get_settings
        settings = get_settings()
        ollama_service = OllamaService(
            host=settings.OLLAMA_HOST,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT
        )
        
    try:
        agent = ObjectArchitectAgent(ollama_service)
        obj = await agent.generate_object(q)
        return obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

