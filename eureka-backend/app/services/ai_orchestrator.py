from app.services.ollama_service import OllamaService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class AIOrchestrator:
    def __init__(self, ollama_service: OllamaService):
        self.ollama = ollama_service
        self.settings = get_settings()
    
    SYSTEM_PROMPT = """You are EUREKA - an AI-powered virtual research laboratory system.

Your mission: Enable researchers and students to conduct experiments at any scale,
from atomic structures to complex biological systems, with real-time AI-powered analysis.

Core principles:
1. Scientific accuracy: All responses must be grounded in established physics, chemistry, and biology
2. Accessibility: Explain complex concepts clearly for all knowledge levels
3. Innovation: Suggest novel experiments and research directions
4. Safety: Warn about dangerous reactions or procedures
5. Honesty: Admit limitations and uncertainties

When responding:
- Cite your sources when using research data
- Provide numerical precision when calculating
- Suggest follow-up experiments
- Flag any unusual or dangerous results
- Connect to real-world applications"""
    
    async def process_user_query(
        self, 
        user_message: str, 
        experiment_context: dict = None,
        conversation_history: list = None
    ) -> str:
        """Process user query and return AI response"""
        
        # Build context-aware prompt
        context_prompt = self._build_context_prompt(
            user_message, 
            experiment_context, 
            conversation_history
        )
        
        # Generate response
        response = await self.ollama.generate(
            prompt=context_prompt,
            system=self.SYSTEM_PROMPT
        )
        
        return response
    
    async def stream_user_query(
        self, 
        user_message: str, 
        experiment_context: dict = None,
        conversation_history: list = None
    ):
        """Stream response for real-time updates"""
        
        context_prompt = self._build_context_prompt(
            user_message, 
            experiment_context, 
            conversation_history
        )
        
        async for chunk in self.ollama.stream_generate(
            prompt=context_prompt,
            system=self.SYSTEM_PROMPT
        ):
            yield chunk
    
    def _build_context_prompt(
        self, 
        user_message: str, 
        experiment_context: dict = None,
        conversation_history: list = None
    ) -> str:
        """Build a context-aware prompt"""
        
        prompt = f"User Query: {user_message}\n"
        
        if experiment_context:
            prompt += f"\n--- Current Experiment Context ---\n"
            prompt += f"Experiment: {experiment_context.get('name', 'Unknown')}\n"
            prompt += f"Objective: {experiment_context.get('objective', 'Unknown')}\n"
            if experiment_context.get('structures'):
                prompt += f"Current Structures: {experiment_context['structures']}\n"
        
        if conversation_history:
            prompt += f"\n--- Conversation History ---\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                prompt += f"User: {msg.get('user', '')}\n"
                prompt += f"Assistant: {msg.get('assistant', '')}\n"
        
        return prompt
    
    async def health_check(self) -> dict:
        """Check system health"""
        ollama_health = await self.ollama.health_check()
        
        return {
            "status": "healthy" if ollama_health else "unhealthy",
            "ollama": "online" if ollama_health else "offline",
            "model": self.settings.OLLAMA_MODEL
        }
