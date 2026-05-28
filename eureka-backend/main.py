from fastapi import FastAPI, WebSocket, HTTPException, Request, Response, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
import os
import shutil
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import get_settings
from app.security import require_role, validate_security_config, verify_websocket_token
from app.services.ollama_service import OllamaService
from app.services.agent_manager import AgentManager
from app.websocket.manager import ConnectionManager
from app.api.simulations import router as simulations_router, sim_manager
from app.api.collaboration import router as collaboration_router
from app.api.health import router as health_router
from app.api.objects import router as objects_router
from app.api.experiments import router as experiments_router
from app.websocket.simulation_stream import SimulationStreamManager

logger = logging.getLogger(__name__)

# Global services
ollama_service = None
agent_manager = None
connection_manager = ConnectionManager()
stream_manager = SimulationStreamManager(sim_manager)
RATE_BUCKETS: dict[str, list[float]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    global ollama_service, agent_manager
    
    settings = get_settings()
    validate_security_config()
    
    # Startup
    logger.info("Starting EUREKA with Multi-Agent System...")
    ollama_service = OllamaService(
        host=settings.OLLAMA_HOST,
        model=settings.OLLAMA_MODEL,
        timeout=settings.OLLAMA_TIMEOUT
    )
    agent_manager = AgentManager(ollama_service)
    
    # Check health
    health = await ollama_service.health_check()
    logger.info(f"Ollama status: {'Online' if health else 'Offline'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EUREKA...")
    await ollama_service.close()

app = FastAPI(
    title="EUREKA Multi-Agent System",
    description="AI-Powered Virtual Research Laboratory with Multi-Agent Architecture",
    version="3.0.0",
    lifespan=lifespan
)

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    REQUEST_COUNT = Counter("eureka_http_requests_total", "HTTP requests", ["method", "path", "status"])
    REQUEST_LATENCY = Histogram("eureka_http_request_seconds", "HTTP request latency", ["method", "path"])
except Exception:
    REQUEST_COUNT = None
    REQUEST_LATENCY = None
    CONTENT_TYPE_LATEST = "text/plain"


@app.middleware("http")
async def production_guardrails(request: Request, call_next):
    settings = get_settings()
    now = time.time()
    client_ip = request.client.host if request.client else "unknown"
    bucket = RATE_BUCKETS.setdefault(client_ip, [])
    cutoff = now - 60
    RATE_BUCKETS[client_ip] = [stamp for stamp in bucket if stamp > cutoff]
    if len(RATE_BUCKETS[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        return Response("Rate limit exceeded", status_code=429)
    RATE_BUCKETS[client_ip].append(now)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return Response("Request body too large", status_code=413)
        except ValueError:
            return Response("Invalid Content-Length", status_code=400)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    path = request.url.path
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self' http://localhost:8000 ws://localhost:8000 https://en.wikipedia.org; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "worker-src 'self' blob:; "
        "media-src 'self' blob:; "
        "frame-ancestors 'self'"
    )

    if REQUEST_COUNT and REQUEST_LATENCY:
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)

    logger.info(
        "http_request method=%s path=%s status=%s duration_ms=%s",
        request.method,
        path,
        response.status_code,
        int(elapsed * 1000),
    )
    return response

# Static files for 3D generated models
os.makedirs("app/data/models", exist_ok=True)
app.mount("/static/models", StaticFiles(directory="app/data/models"), name="models")

# Register routers
app.include_router(simulations_router)
app.include_router(collaboration_router)
app.include_router(health_router)
app.include_router(objects_router)
app.include_router(experiments_router)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 3D GENERATION ENDPOINT ============

@app.post("/api/3d/generate")
async def generate_3d_model(file: UploadFile = File(...)):
    """
    Receives image from frontend, sends to RunPod Serverless API (TripoSR),
    saves the returned GLB to storage, and returns the URL.
    """
    # 1. Forward to AI Compute (RunPod GPU)
    # Using local mock endpoint for now since we haven't deployed to actual RunPod
    runpod_url = "http://localhost:8001/generate" 
    
    try:
        # Read the uploaded file
        file_bytes = await file.read()
        
        # Send to GPU inference service
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {'file': (file.filename, file_bytes, file.content_type)}
            response = await client.post(runpod_url, files=files)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"GPU service failed: {response.text}")
                
            # 2. Save to Storage (Simulating Firebase Storage / S3 via local static files)
            # In a real production setup, we'd use firebase_admin.storage here
            filename = f"gen_{int(time.time())}.glb"
            filepath = os.path.join("app/data/models", filename)
            
            with open(filepath, "wb") as f:
                f.write(response.content)
                
            # 3. Return the public URL
            public_url = f"http://localhost:8000/static/models/{filename}"
            return {"status": "success", "model_url": public_url}
            
    except Exception as e:
        logger.error(f"3D Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check

@app.get("/health")
async def health_check():
    """Check system health"""
    ollama_health = await ollama_service.health_check()
    return {
        "status": "healthy" if ollama_health else "degraded",
        "ollama": "online" if ollama_health else "offline",
        "agents": "ready",
        "version": "3.0.0"
    }


@app.get("/metrics")
async def metrics():
    if not REQUEST_COUNT:
        return Response("prometheus_client not installed\n", media_type="text/plain")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Multi-agent Endpoints

@app.post("/api/agents/process")
async def process_with_agents(
    message: str,
    experiment_id: str = None,
    experiment_context: dict = None,
    user: dict = Depends(require_role("editor"))
):
    """Process request through multi-agent system"""
    try:
        settings = get_settings()
        if len(message) > settings.MAX_AI_PROMPT_CHARS:
            raise HTTPException(status_code=413, detail="Message exceeds AI prompt limit")
        result = await agent_manager.process_request(
            user_message=message,
            experiment_context=experiment_context
        )
        
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/stream")
async def stream_agents_response(
    message: str,
    experiment_id: str = None,
    experiment_context: dict = None,
    user: dict = Depends(require_role("editor"))
):
    """Stream response from multi-agent system"""
    try:
        settings = get_settings()
        if len(message) > settings.MAX_AI_PROMPT_CHARS:
            raise HTTPException(status_code=413, detail="Message exceeds AI prompt limit")
        async def generate():
            async for chunk in agent_manager.stream_request(
                user_message=message,
                experiment_context=experiment_context
            ):
                yield chunk
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Specific Agent Endpoints

@app.post("/api/agents/explain")
async def explain(
    concept: str,
    context: dict = None,
    user: dict = Depends(require_role("viewer"))
):
    """Use Explainer Agent"""
    try:
        from app.agents.explainer_agent import ExplainerAgent
        agent = ExplainerAgent(ollama_service)
        response = await agent.process({
            "question": concept,
            "context": context or {}
        })
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/analyze")
async def analyze(
    molecule: str,
    analysis_type: str = "comprehensive",
    context: dict = None,
    user: dict = Depends(require_role("viewer"))
):
    """Use Analyzer Agent"""
    try:
        from app.agents.analyzer_agent import AnalyzerAgent
        agent = AnalyzerAgent(ollama_service)
        response = await agent.process({
            "molecule": molecule,
            "analysis_type": analysis_type,
            "context": context or {}
        })
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/predict")
async def predict(
    scenario: str,
    variables: dict = None,
    context: dict = None,
    user: dict = Depends(require_role("editor"))
):
    """Use Thinker Agent"""
    try:
        from app.agents.thinker_agent import ThinkerAgent
        agent = ThinkerAgent(ollama_service)
        response = await agent.process({
            "scenario": scenario,
            "variables": variables or {},
            "context": context or {}
        })
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/research")
async def research(
    query: str,
    context: dict = None,
    user: dict = Depends(require_role("viewer"))
):
    """Use Research Integrator Agent"""
    try:
        from app.agents.research_agent import ResearchIntegratorAgent
        agent = ResearchIntegratorAgent(ollama_service)
        response = await agent.process({
            "query": query,
            "context": context or {}
        })
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Experiments (Phase 2 Compatibility)

@app.post("/api/experiments")
async def create_experiment(name: str, objective: str, user: dict = Depends(require_role("editor"))):
    """Create new experiment"""
    return {
        "status": "success",
        "experiment_id": "exp_123",
        "name": name,
        "objective": objective
    }

@app.get("/api/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, user: dict = Depends(require_role("viewer"))):
    """Get experiment details"""
    return {
        "experiment_id": experiment_id,
        "name": "Sample Experiment",
        "status": "active"
    }

# Websocket

@app.websocket("/ws/experiment/{experiment_id}")
async def websocket_endpoint(websocket: WebSocket, experiment_id: str):
    """WebSocket for real-time multi-agent responses"""
    verify_websocket_token(websocket, "viewer")
    await connection_manager.connect(websocket, experiment_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            message = data.get("message")
            context = data.get("context", {})
            settings = get_settings()
            if not isinstance(message, str) or len(message) > settings.MAX_AI_PROMPT_CHARS:
                await websocket.send_json({"type": "error", "message": "Invalid or oversized message"})
                continue
            
            # Process through multi-agent system
            result = await agent_manager.process_request(
                user_message=message,
                experiment_context=context
            )
            
            # Broadcast result
            await connection_manager.broadcast(
                experiment_id,
                {
                    "type": "agent_response",
                    "data": result,
                    "timestamp": data.get("timestamp")
                }
            )
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await connection_manager.disconnect(websocket, experiment_id)

# Simulation Websocket

@app.websocket("/ws/simulation/{sim_id}")
async def simulation_websocket_endpoint(websocket: WebSocket, sim_id: str):
    """WebSocket for real-time simulation streaming"""
    verify_websocket_token(websocket, "viewer")
    await stream_manager.stream_simulation(websocket, sim_id)

# Root

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to EUREKA Multi-Agent System",
        "version": "3.0.0",
        "agents": ["Explainer", "Analyzer", "Thinker", "Research", "Helper"],
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
