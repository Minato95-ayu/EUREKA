import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.ollama_service import OllamaService
from app.agents.explainer_agent import ExplainerAgent
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.thinker_agent import ThinkerAgent
from app.services.agent_manager import AgentManager

@pytest.fixture
def mock_ollama_service():
    """Fixture to mock Ollama service to run tests without a local Ollama server"""
    service = MagicMock(spec=OllamaService)
    
    # Mock generate
    async def mock_generate(prompt: str, system: str = None) -> str:
        if "synthesis" in prompt.lower() or "synthesize" in prompt.lower():
            return '{"status": "success", "unified_response": "Mocked unified response from Helper agent coordination."}'
        if "covalent bond" in prompt.lower() or "explain" in prompt.lower():
            return "Covalent bond is a chemical bond that involves the sharing of electron pairs between atoms."
        if "h2o" in prompt.lower() or "molecule" in prompt.lower():
            return "Molecular weight of H2O: 18.015 g/mol. Thermodynamic properties: stable."
        if "heat water" in prompt.lower() or "scenario" in prompt.lower():
            return "Water will boil and turn into steam at 100°C under 1 atm pressure."
        return "Mocked Ollama response."
        
    service.generate = AsyncMock(side_effect=mock_generate)
    
    # Mock stream_generate
    async def mock_stream_generate(prompt: str, system: str = None):
        yield "Mocked "
        yield "stream "
        yield "chunk."
    service.stream_generate = mock_stream_generate
    
    return service

@pytest.mark.asyncio
async def test_explainer_agent(mock_ollama_service):
    """Test Explainer Agent"""
    agent = ExplainerAgent(mock_ollama_service)
    response = await agent.process({
        "question": "What is a covalent bond?",
        "context": {}
    })
    assert response
    assert len(response) > 0
    assert "sharing of electron" in response.lower()

@pytest.mark.asyncio
async def test_analyzer_agent(mock_ollama_service):
    """Test Analyzer Agent"""
    agent = AnalyzerAgent(mock_ollama_service)
    response = await agent.process({
        "molecule": "H2O",
        "analysis_type": "comprehensive"
    })
    assert response
    assert "weight" in response.lower() or "h2o" in response.lower()

@pytest.mark.asyncio
async def test_thinker_agent(mock_ollama_service):
    """Test Thinker Agent"""
    agent = ThinkerAgent(mock_ollama_service)
    response = await agent.process({
        "scenario": "What happens if we heat water to 150°C?",
        "variables": {"temperature": "150C"}
    })
    assert response
    assert len(response) > 0
    assert "boil" in response.lower() or "steam" in response.lower()

@pytest.mark.asyncio
async def test_agent_manager(mock_ollama_service):
    """Test Agent Manager"""
    manager = AgentManager(mock_ollama_service)
    result = await manager.process_request(
        user_message="Explain water and predict what happens if we heat it",
        experiment_context={
            "experiment": "Water Analysis",
            "current_molecule": "H2O",
            "variables": {"temperature": "150C"}
        }
    )
    assert result["status"] == "success"
    assert "agents_used" in result
    assert "unified_response" in result
