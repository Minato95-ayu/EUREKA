from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
from contextlib import asynccontextmanager

from app.config import get_settings
from app.services.ollama_service import OllamaService
from app.services.agent_manager import AgentManager
from app.websocket.manager import ConnectionManager
from app.api.simulations import router as simulations_router, sim_manager
from app.api.collaboration import router as collaboration_router
from app.api.health import router as health_router
from app.websocket.simulation_stream import SimulationStreamManager

logger = logging.getLogger(__name__)

# Global services
ollama_service = None
agent_manager = None
connection_manager = ConnectionManager()
stream_manager = SimulationStreamManager(sim_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    global ollama_service, agent_manager
    
    settings = get_settings()
    
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

# Register routers
app.include_router(simulations_router)
app.include_router(collaboration_router)
app.include_router(health_router)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ HEALTH CHECK ============

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

# ============ MULTI-AGENT ENDPOINTS ============

@app.post("/api/agents/process")
async def process_with_agents(
    message: str,
    experiment_id: str = None,
    experiment_context: dict = None
):
    """Process request through multi-agent system"""
    try:
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
    experiment_context: dict = None
):
    """Stream response from multi-agent system"""
    try:
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

# ============ SPECIFIC AGENT ENDPOINTS ============

@app.post("/api/agents/explain")
async def explain(
    concept: str,
    context: dict = None
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
    context: dict = None
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
    context: dict = None
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
    context: dict = None
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

# ============ EXPERIMENTS (Phase 2 Compatibility) ============

@app.post("/api/experiments")
async def create_experiment(name: str, objective: str):
    """Create new experiment"""
    return {
        "status": "success",
        "experiment_id": "exp_123",
        "name": name,
        "objective": objective
    }

@app.get("/api/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details"""
    return {
        "experiment_id": experiment_id,
        "name": "Sample Experiment",
        "status": "active"
    }

# ============ WEBSOCKET ============

@app.websocket("/ws/experiment/{experiment_id}")
async def websocket_endpoint(websocket: WebSocket, experiment_id: str):
    """WebSocket for real-time multi-agent responses"""
    await connection_manager.connect(websocket, experiment_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            message = data.get("message")
            context = data.get("context", {})
            
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

# ============ SIMULATION WEBSOCKET ============

@app.websocket("/ws/simulation/{sim_id}")
async def simulation_websocket_endpoint(websocket: WebSocket, sim_id: str):
    """WebSocket for real-time simulation streaming"""
    await stream_manager.stream_simulation(websocket, sim_id)

# ============ ROOT ============

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
