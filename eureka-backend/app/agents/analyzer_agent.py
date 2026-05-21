from app.agents.base_agent import BaseAgent
from typing import Dict, Any
import logging
import json

logger = logging.getLogger(__name__)

class AnalyzerAgent(BaseAgent):
    """Calculates and measures molecular properties"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "Analyzer")
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Analyzer Agent. Your role is to calculate 
and measure all properties of molecular structures and reactions.

Your expertise:
- Molecular weight calculations
- Bond angle and length predictions
- Thermodynamic calculations
- Spectroscopic properties
- Stability analysis
- Energy calculations
- Reaction kinetics

When analyzing:
1. Calculate exact molecular properties
2. Use established scientific formulas
3. Provide numerical precision with units
4. Include relevant constants
5. Flag any unusual or dangerous results
6. Cite the formulas used

Always provide:
- Numerical values with units
- Calculation methodology
- Confidence level
- Relevant references"""
    
    async def process(self, request: Dict[str, Any]) -> str:
        """Process analysis request"""
        
        molecule = request.get("molecule", "")
        analysis_type = request.get("analysis_type", "general")
        context = request.get("context", {})
        
        context_str = self._build_context(context)
        
        prompt = f"""{context_str}

Molecule/Structure: {molecule}
Analysis Type: {analysis_type}

Provide detailed numerical analysis including:
1. Molecular weight
2. Structural properties (if applicable)
3. Thermodynamic properties
4. Spectroscopic predictions
5. Stability assessment
6. Any warnings or special considerations

Format as structured data with units."""
        
        response = await self.generate_response(prompt)
        logger.info(f"Analyzer processed: {molecule[:50]}...")
        
        return response

async def analyze_molecule(ollama_service, molecule: str):
    agent = AnalyzerAgent(ollama_service)
    request = {
        "molecule": molecule,
        "analysis_type": "comprehensive"
    }
    return await agent.process(request)
