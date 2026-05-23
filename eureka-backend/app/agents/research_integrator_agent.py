from app.agents.base_agent import BaseAgent

class ResearchIntegratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Research Integrator Agent",
            role="You are the EUREKA Research Integrator Agent. Search relevant research databases, find similar experiments, compare results, provide citations, and identify research gaps."
        )

research_integrator_agent = ResearchIntegratorAgent()
