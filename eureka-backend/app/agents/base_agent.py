from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all EUREKA agents"""
    
    def __init__(self, ollama_service: OllamaService, name: str):
        self.ollama = ollama_service
        self.name = name
        self.system_prompt = self._get_system_prompt()
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return agent's system prompt"""
        pass
    
    @abstractmethod
    async def process(self, request: Dict[str, Any]) -> str:
        """Process request and return response"""
        pass
    
    async def generate_response(self, prompt: str) -> str:
        """Generate response using Ollama"""
        return await self.ollama.generate(
            prompt=prompt,
            system=self.system_prompt
        )
    
    async def stream_response(self, prompt: str):
        """Stream response from Ollama"""
        async for chunk in self.ollama.stream_generate(
            prompt=prompt,
            system=self.system_prompt
        ):
            yield chunk
    
    def _build_context(self, context: Dict) -> str:
        """Build context string from dictionary"""
        context_str = ""
        if context.get("experiment"):
            context_str += f"Experiment: {context['experiment']}\n"
        if context.get("structures"):
            context_str += f"Structures: {context['structures']}\n"
        if context.get("history"):
            context_str += f"History: {context['history']}\n"
        return context_str
