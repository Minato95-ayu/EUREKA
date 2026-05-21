from app.agents.helper_agent import HelperAgent
from app.services.ollama_service import OllamaService
from typing import Dict, Any
import logging
import hashlib
import time
from app.database import db

logger = logging.getLogger(__name__)

async def log_agent_metrics(agent_name: str, response_time: int, success: bool, error: str = None):
    """Log agent performance metrics"""
    await db.execute("""
        INSERT INTO agent_metrics (agent_name, response_time_ms, success, error_message)
        VALUES ($1, $2, $3, $4)
    """, agent_name, response_time, success, error)

class AgentManager:
    """Manages all agents and coordinates their execution"""
    
    def __init__(self, ollama_service: OllamaService):
        self.ollama = ollama_service
        self.helper = HelperAgent(ollama_service)
        self.response_cache = {}
    
    def _get_cache_key(self, message: str, context: dict) -> str:
        """Generate cache key"""
        key_str = f"{message}:{str(context)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def process_request(
        self, 
        user_message: str,
        experiment_context: Dict[str, Any] = None,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """Process user request through agent system with caching and metrics logging"""
        
        start_time = time.time()
        cache_key = self._get_cache_key(user_message, experiment_context or {})
        
        # Check cache
        if cache_key in self.response_cache:
            logger.info("Cache hit")
            elapsed_ms = int((time.time() - start_time) * 1000)
            await log_agent_metrics("Helper (Cache Hit)", elapsed_ms, True)
            return self.response_cache[cache_key]
        
        try:
            # Build request
            request = {
                "message": user_message,
                "context": experiment_context or {},
                "history": conversation_history or []
            }
            
            # Process through helper agent
            result = await self.helper.process(request)
            
            # Cache result
            self.response_cache[cache_key] = result
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            await log_agent_metrics("Helper", elapsed_ms, True)
            
            # Log metrics for used sub-agents as well
            agents_used = result.get("agents_used", [])
            for agent in agents_used:
                await log_agent_metrics(agent.capitalize(), elapsed_ms, True)
            
            logger.info(f"Request processed successfully")
            return result
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            await log_agent_metrics("Helper", elapsed_ms, False, str(e))
            logger.error(f"Error processing request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def stream_request(
        self, 
        user_message: str,
        experiment_context: Dict[str, Any] = None
    ):
        """Stream response for real-time updates"""
        
        try:
            request = {
                "message": user_message,
                "context": experiment_context or {}
            }
            
            # Stream through helper agent
            async for chunk in self.helper.stream_response(user_message):
                yield chunk
                
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"Error: {str(e)}"
