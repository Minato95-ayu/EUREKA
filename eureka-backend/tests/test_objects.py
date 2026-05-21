import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.object_library import ObjectLibrary


def test_object_library_search_car_engine():
    library = ObjectLibrary()

    results = library.search("car engine")

    assert len(results) >= 1
    assert results[0].id == "car_engine"
    assert results[0].component_count >= 5


def test_object_library_component_lookup():
    library = ObjectLibrary()

    component = library.get_component("car_engine", "piston")

    assert component is not None
    assert component.name == "Piston"
    assert "Compresses" in component.function


def test_object_api_search():
    client = TestClient(app)
    response = client.get("/api/objects/search?q=piston")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "car_engine"
