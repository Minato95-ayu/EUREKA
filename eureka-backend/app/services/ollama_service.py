import httpx
import json
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, host: str, model: str, timeout: int):
        self.host = host
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def generate(self, prompt: str, system: str = None) -> str:
        """Generate response from Llama 3"""
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            
            response = await self.client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
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
            
            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
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
        """Check if Ollama is running"""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
