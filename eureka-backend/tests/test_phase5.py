import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from app.services.collaboration_service import CollaborationService, CollaborationRole
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.services.research_database import ResearchDatabaseService

@pytest.fixture
def collab_service():
    return CollaborationService()

@pytest.fixture
def analytics_service():
    return AnalyticsService()

@pytest.fixture
def export_service():
    return ExportService()

@pytest.fixture
def research_db_service():
    # Pass a local/test DB URL; it will fallback to offline/in-memory mode if DB is unavailable
    return ResearchDatabaseService("sqlite:///:memory:")

@pytest.mark.asyncio
async def test_create_collaboration(collab_service):
    """Test collaboration creation"""
    collab_id = await collab_service.create_collaboration(
        experiment_id="exp_001",
        owner_id="user_001",
        title="Water Analysis",
        description="Collaborative water study"
    )
    
    assert collab_id is not None
    assert collab_id in collab_service.collaborations
    
    state = await collab_service.get_collaboration_state(collab_id)
    assert state["title"] == "Water Analysis"
    assert state["owner_id"] == "user_001"
    assert "user_001" in state["members"]
    assert state["members"]["user_001"]["role"] == "owner"

@pytest.mark.asyncio
async def test_add_collaborator(collab_service):
    """Test adding collaborator"""
    collab_id = await collab_service.create_collaboration(
        experiment_id="exp_001",
        owner_id="user_001",
        title="Test"
    )
    
    success = await collab_service.add_collaborator(
        collab_id=collab_id,
        user_id="user_002",
        role="editor"
    )
    
    assert success
    state = await collab_service.get_collaboration_state(collab_id)
    assert "user_002" in state["members"]
    assert state["members"]["user_002"]["role"] == "editor"

@pytest.mark.asyncio
async def test_comments_and_versions(collab_service):
    """Test adding comments and versions"""
    collab_id = await collab_service.create_collaboration(
        experiment_id="exp_001",
        owner_id="user_001",
        title="Versioning Lab"
    )
    
    # Test add comment
    comment = await collab_service.add_comment(
        collab_id=collab_id,
        user_id="user_002",
        text="Check this value.",
        line_number=42
    )
    assert "error" not in comment
    assert comment["text"] == "Check this value."
    assert comment["line_number"] == 42
    
    # Test create version
    exp_data = {"particles": [{"id": 1, "pos": [0,0,0]}]}
    version = await collab_service.create_version(
        collab_id=collab_id,
        user_id="user_001",
        data=exp_data,
        message="Initial state snapshot"
    )
    assert "error" not in version
    assert version["message"] == "Initial state snapshot"
    assert version["data"] == exp_data

@pytest.mark.asyncio
async def test_analytics_comparison(analytics_service):
    """Test experiment comparison"""
    # Add sample data
    analytics_service.experiments_data["exp_001"] = [
        {"value": 10, "timestamp": "2026-05-19T10:00:00"},
        {"value": 12, "timestamp": "2026-05-19T10:01:00"}
    ]
    analytics_service.experiments_data["exp_002"] = [
        {"value": 15, "timestamp": "2026-05-19T10:00:00"},
        {"value": 18, "timestamp": "2026-05-19T10:01:00"}
    ]
    
    comparison = await analytics_service.compare_experiments(["exp_001", "exp_002"])
    
    assert "metrics" in comparison
    assert "statistics" in comparison
    assert "insights" in comparison
    
    assert comparison["metrics"]["exp_001"]["mean"] == 11.0
    assert comparison["metrics"]["exp_002"]["mean"] == 16.5

@pytest.mark.asyncio
async def test_analytics_anomalies_and_trends(analytics_service):
    """Test anomaly detection and trend analysis"""
    analytics_service.experiments_data["exp_001"] = [
        {"value": 10.0, "timestamp": "2026-05-19T10:00:00"},
        {"value": 10.2, "timestamp": "2026-05-19T10:01:00"},
        {"value": 10.1, "timestamp": "2026-05-19T10:02:00"},
        {"value": 100.0, "timestamp": "2026-05-19T10:03:00"},  # Anomaly
        {"value": 9.9, "timestamp": "2026-05-19T10:04:00"}
    ]
    
    anomalies = await analytics_service.detect_anomalies("exp_001", threshold=1.5)
    assert len(anomalies) == 1
    assert anomalies[0]["value"] == 100.0
    
    trends = await analytics_service.trend_analysis("exp_001")
    assert "trend" in trends
    assert "slope" in trends

@pytest.mark.asyncio
async def test_export_json(export_service):
    """Test JSON export"""
    experiment = {
        "name": "Test",
        "description": "Test experiment",
        "created_at": "2026-05-19T10:00:00",
        "results": {}
    }
    
    json_data = await export_service.export_json(experiment)
    assert json_data is not None
    assert "Test" in json_data
    
    parsed = json.loads(json_data)
    assert parsed["name"] == "Test"

@pytest.mark.asyncio
async def test_export_csv_and_pdf(export_service):
    """Test CSV and PDF document generation"""
    experiment = {
        "name": "Water Molecule Simulation",
        "description": "H2O molecular trajectory study",
        "created_at": "2026-05-21T10:00:00",
        "results": {
            "final_energy": -342.12,
            "simulation_time": 10.0,
            "trajectory": [
                {
                    "time": 0.0,
                    "particles": [
                        {"id": "H1", "position": [1.0, 0.0, 0.0], "velocity": [0.1, 0.0, 0.0]},
                        {"id": "O1", "position": [0.0, 0.0, 0.0], "velocity": [0.0, 0.0, 0.0]}
                    ]
                }
            ]
        }
    }
    
    # Test CSV
    csv_data = await export_service.export_csv(experiment)
    assert "H2O molecular trajectory study" in csv_data
    assert "H1" in csv_data
    
    # Test PDF
    pdf_bytes = await export_service.export_pdf(experiment)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF starts with %PDF magic header
    assert pdf_bytes.startswith(b"%PDF")
    
    # Test DOI
    doi = await export_service.generate_doi("exp_123456789")
    assert doi.startswith("10.5555/eureka.exp_1234")

@pytest.mark.asyncio
async def test_research_database_arxiv_mock(research_db_service):
    """Test ArXiv XML parser with mock API call"""
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2101.00001v1</id>
        <title>Quantum Mechanics in Molecular Bonds</title>
        <summary>This paper covers quantum state transitions in molecules.</summary>
        <published>2026-05-21T00:00:00Z</published>
        <author>
          <name>Dr. John Doe</name>
        </author>
      </entry>
    </feed>
    """
    
    with patch.object(research_db_service.http_client, "get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=mock_xml)
        
        papers = await research_db_service.search_arxiv("quantum mechanics")
        assert len(papers) == 1
        assert papers[0]["title"] == "Quantum Mechanics in Molecular Bonds"
        assert papers[0]["arxiv_id"] == "2101.00001"
        assert "Dr. John Doe" in papers[0]["authors"]
        
        # Test getting related papers by keyword overlap
        related = await research_db_service.get_related_papers(papers[0]["id"])
        # Should be empty or match if other papers cached
        assert isinstance(related, list)
