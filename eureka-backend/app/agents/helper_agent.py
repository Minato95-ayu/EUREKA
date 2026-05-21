from app.agents.base_agent import BaseAgent
from app.agents.explainer_agent import ExplainerAgent
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.thinker_agent import ThinkerAgent
from app.agents.research_agent import ResearchIntegratorAgent
from typing import Dict, Any
import logging
import json

logger = logging.getLogger(__name__)

class HelperAgent(BaseAgent):
    """Master coordinator that orchestrates all agents"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "Helper")
        self.explainer = ExplainerAgent(ollama_service)
        self.analyzer = AnalyzerAgent(ollama_service)
        self.thinker = ThinkerAgent(ollama_service)
        self.research = ResearchIntegratorAgent(ollama_service)
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Helper Agent - the Master Coordinator.

Your role:
1. Understand user requests
2. Determine which agents to consult
3. Coordinate agent responses
4. Synthesize insights into unified response
5. Provide actionable recommendations

You have access to:
- Explainer Agent: Explains concepts
- Analyzer Agent: Calculates properties
- Thinker Agent: Predicts outcomes
- Research Agent: Finds related research

When coordinating:
1. Analyze the user's request
2. Decide which agents are needed
3. Collect their insights
4. Synthesize into coherent response
5. Provide clear recommendations"""
    
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request and coordinate agents"""
        
        user_message = request.get("message", "")
        experiment_context = request.get("context", {})
        
        logger.info(f"Helper processing: {user_message[:50]}...")
        
        # Determine which agents to use
        agents_needed = self._determine_agents(user_message)
        logger.info(f"Agents needed: {agents_needed}")
        
        # Collect responses from agents
        agent_responses = {}
        
        if "explainer" in agents_needed:
            agent_responses["explainer"] = await self.explainer.process({
                "question": user_message,
                "context": experiment_context
            })
        
        if "analyzer" in agents_needed:
            agent_responses["analyzer"] = await self.analyzer.process({
                "molecule": experiment_context.get("current_molecule", ""),
                "context": experiment_context
            })
        
        if "thinker" in agents_needed:
            agent_responses["thinker"] = await self.thinker.process({
                "scenario": user_message,
                "variables": experiment_context.get("variables", {}),
                "context": experiment_context
            })
        
        if "research" in agents_needed:
            agent_responses["research"] = await self.research.process({
                "query": user_message,
                "context": experiment_context
            })
        
        # Synthesize responses
        unified_response = await self._synthesize_responses(
            user_message,
            agent_responses,
            experiment_context
        )
        
        return {
            "status": "success",
            "message": user_message,
            "agents_used": agents_needed,
            "agent_responses": agent_responses,
            "unified_response": unified_response
        }
    
    def _determine_agents(self, message: str) -> list:
        """Determine which agents are needed"""
        
        message_lower = message.lower()
        agents = []
        
        # Keyword-based agent selection
        if any(word in message_lower for word in ["explain", "what is", "how does", "understand"]):
            agents.append("explainer")
        
        if any(word in message_lower for word in ["calculate", "weight", "property", "analyze", "measure"]):
            agents.append("analyzer")
        
        if any(word in message_lower for word in ["predict", "what if", "happen", "result", "outcome"]):
            agents.append("thinker")
        
        if any(word in message_lower for word in ["research", "paper", "study", "similar", "compare"]):
            agents.append("research")
        
        # If no agents determined, use all
        if not agents:
            agents = ["explainer", "analyzer"]
        
        return agents
    
    async def _synthesize_responses(
        self, 
        user_message: str, 
        agent_responses: Dict[str, str],
        context: Dict
    ) -> str:
        """Synthesize agent responses into unified response"""
        
        responses_str = json.dumps(agent_responses, indent=2)
        
        synthesis_prompt = f"""User Request: {user_message}

Agent Responses:
{responses_str}

Synthesize these responses into a single, coherent answer that:
1. Directly addresses the user's question
2. Incorporates insights from all agents
3. Provides clear recommendations
4. Suggests next steps
5. Highlights any important warnings or considerations

Provide a professional, comprehensive response."""
        
        unified = await self.generate_response(synthesis_prompt)
        
        return unified
