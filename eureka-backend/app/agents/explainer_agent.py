from app.agents.base_agent import BaseAgent
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ExplainerAgent(BaseAgent):
    """Explains scientific concepts clearly"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "Explainer")
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Explainer Agent. Your role is to make complex 
scientific concepts understandable to researchers and students.

Your expertise:
- Atomic structure and bonding
- Chemical reactions mechanisms
- Biological processes
- Physics principles
- Historical context of discoveries

When explaining:
1. Start with fundamental concepts
2. Build complexity gradually
3. Use analogies when helpful
4. Provide real-world examples
5. Connect to applications

Be clear, engaging, and accessible. Avoid jargon when possible, 
but define technical terms when necessary."""
    
    async def process(self, request: Dict[str, Any]) -> str:
        """Process explanation request"""
        
        question = request.get("question", "")
        context = request.get("context", {})
        
        context_str = self._build_context(context)
        
        prompt = f"""{context_str}

User Question: {question}

Provide a clear, engaging explanation that:
1. Addresses the question directly
2. Explains underlying principles
3. Uses analogies or examples
4. Connects to real-world applications
5. Suggests follow-up questions"""
        
        response = await self.generate_response(prompt)
        logger.info(f"Explainer processed: {question[:50]}...")
        
        return response

# Usage example
async def explain_concept(ollama_service, concept: str):
    agent = ExplainerAgent(ollama_service)
    request = {
        "question": f"Explain {concept}",
        "context": {"experiment": "Water Analysis"}
    }
    return await agent.process(request)
