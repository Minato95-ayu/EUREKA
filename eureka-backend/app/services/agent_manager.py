from app.agents.helper_agent import HelperAgent
from app.services.ollama_service import OllamaService
from typing import Dict, Any
import logging
import hashlib
import time
import json
from app.database import db
from app.config import get_settings

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
        self.redis_client = None
        try:
            import redis
            settings = get_settings()
            self.redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
            self.redis_client.ping()
        except Exception as e:
            logger.info(f"Redis agent cache unavailable; using process cache only: {e}")
    
    def _get_cache_key(self, message: str, context: dict) -> str:
        """Generate cache key"""
        key_str = f"{message}:{str(context)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def _get_cached_response(self, cache_key: str) -> Dict[str, Any] | None:
        if self.redis_client:
            try:
                import asyncio
                raw = await asyncio.to_thread(self.redis_client.get, f"agent_cache:{cache_key}")
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        return self.response_cache.get(cache_key)

    async def _set_cached_response(self, cache_key: str, result: Dict[str, Any]) -> None:
        self.response_cache[cache_key] = result
        if self.redis_client:
            try:
                import asyncio
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"agent_cache:{cache_key}",
                    600,
                    json.dumps(result, default=str),
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
    
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
        cached = await self._get_cached_response(cache_key)
        if cached:
            logger.info("Cache hit")
            elapsed_ms = int((time.time() - start_time) * 1000)
            await log_agent_metrics("Helper (Cache Hit)", elapsed_ms, True)
            return cached
        
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
            await self._set_cached_response(cache_key, result)
            
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
