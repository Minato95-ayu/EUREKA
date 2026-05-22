import httpx
import json
import time
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, host: str, model: str, timeout: int):
        self.host = host
        self.model = model
        self.timeout = timeout
        # Set connect timeout to 2.0s to avoid hanging long on offline Ollama
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(float(timeout), connect=2.0))
        self._resolved_model = None
        self._health_cached = None
        self._health_timestamp = 0.0
    
    async def resolve_model(self) -> str:
        """Resolve self.model against installed models on the Ollama host."""
        if self._resolved_model:
            return self._resolved_model
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                if self.model in models:
                    self._resolved_model = self.model
                else:
                    for suffix in [":latest", ":8b"]:
                        candidate = f"{self.model}{suffix}"
                        if candidate in models:
                            logger.info(f"Resolved model '{self.model}' to '{candidate}'")
                            self._resolved_model = candidate
                            break
                    else:
                        for m in models:
                            if m.startswith(self.model) or self.model in m:
                                logger.info(f"Resolved model '{self.model}' to '{m}'")
                                self._resolved_model = m
                                break
                        else:
                            self._resolved_model = self.model
            else:
                self._resolved_model = self.model
        except Exception as e:
            logger.warning(f"Error resolving model name: {e}")
            self._resolved_model = self.model
        return self._resolved_model

    async def generate(self, prompt: str, system: str = None, format: str = None, options: dict = None) -> str:
        """Generate response from Llama 3"""
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            resolved_model = await self.resolve_model()
            
            payload = {
                "model": resolved_model,
                "prompt": full_prompt,
                "stream": False,
                "temperature": 0.7,
                "top_p": 0.9,
            }
            if format:
                payload["format"] = format
            if options:
                # Merge or override options
                for k, v in options.items():
                    payload[k] = v
                    
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return "Error generating response"
                
        except Exception as e:
            logger.error(f"Ollama service error: {str(e)}")
            return f"Error: {str(e)}"
    
    async def stream_generate(
        self, 
        prompt: str, 
        system: str = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Llama 3"""
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            resolved_model = await self.resolve_model()
            
            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json={
                    "model": resolved_model,
                    "prompt": full_prompt,
                    "stream": True,
                    "temperature": 0.7,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield data.get("response", "")
                        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def health_check(self) -> bool:
        """Check if Ollama is running (cached for 10 seconds)"""
        now = time.time()
        if self._health_cached is not None and (now - self._health_timestamp) < 10.0:
            return self._health_cached
            
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            is_healthy = response.status_code == 200
            self._health_cached = is_healthy
            self._health_timestamp = now
            if is_healthy:
                try:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    if self.model in models:
                        self._resolved_model = self.model
                    else:
                        for suffix in [":latest", ":8b"]:
                            candidate = f"{self.model}{suffix}"
                            if candidate in models:
                                self._resolved_model = candidate
                                break
                        else:
                            for m in models:
                                if m.startswith(self.model) or self.model in m:
                                    self._resolved_model = m
                                    break
                except Exception as sub_err:
                    logger.warning(f"Error parsing models during health check: {sub_err}")
            return is_healthy
        except Exception as e:
            self._health_cached = False
            self._health_timestamp = now
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
