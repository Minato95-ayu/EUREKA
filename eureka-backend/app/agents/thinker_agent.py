from app.agents.base_agent import BaseAgent
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ThinkerAgent(BaseAgent):
    """Predicts outcomes and suggests innovations"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "Thinker")
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Thinker Agent. Your role is to predict 
outcomes and suggest innovative experiments.

Your expertise:
- Reaction outcome prediction
- "What-if" scenario analysis
- Experimental design
- Risk assessment
- Innovation suggestions
- Pattern recognition
- Trend analysis

When thinking:
1. Apply physics and chemistry laws
2. Consider all variables and constraints
3. Predict multiple possible outcomes
4. Assess probability of each outcome
5. Suggest follow-up experiments
6. Identify risks and opportunities
7. Propose novel approaches

Always:
- Cite the laws/principles used
- Provide confidence levels
- Suggest safety precautions
- Recommend follow-up experiments
- Consider edge cases"""
    
    async def process(self, request: Dict[str, Any]) -> str:
        """Process prediction request"""
        
        scenario = request.get("scenario", "")
        variables = request.get("variables", {})
        context = request.get("context", {})
        
        context_str = self._build_context(context)
        
        variables_str = "\n".join([f"- {k}: {v}" for k, v in variables.items()])
        
        prompt = f"""{context_str}

Scenario: {scenario}

Variables:
{variables_str}

Provide:
1. Predicted outcomes (with probabilities)
2. Underlying principles (physics/chemistry laws)
3. Key factors affecting outcome
4. Suggested follow-up experiments
5. Potential risks and safety considerations
6. Innovative approaches or alternatives"""
        
        response = await self.generate_response(prompt)
        logger.info(f"Thinker processed: {scenario[:50]}...")
        
        return response

async def predict_outcome(ollama_service, scenario: str, variables: Dict):
    agent = ThinkerAgent(ollama_service)
    request = {
        "scenario": scenario,
        "variables": variables
    }
    return await agent.process(request)
