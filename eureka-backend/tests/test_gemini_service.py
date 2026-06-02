"""
Gemini 3D Service tests for EUREKA — generated via ECC tdd-guide agent.
Covers color inference, geometry inference, and service initialization.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from app.services.gemini_3d_service import (
    Gemini3DService,
    _infer_color,
    _infer_geometry,
    MATERIAL_COLORS,
    GEOMETRY_RULES,
)


# ─── Color Inference Tests ────────────────────────────────────────────────────

class TestInferColor:
    def test_steel_material_returns_correct_hex(self):
        assert _infer_color("shaft", "steel") == "#4a4e69"

    def test_aluminum_material(self):
        assert _infer_color("piston", "aluminum") == "#c0c5ce"

    def test_aluminium_spelling_variant(self):
        assert _infer_color("plate", "aluminium") == "#c0c5ce"

    def test_copper_material(self):
        assert _infer_color("coil", "copper") == "#b87333"

    def test_rubber_material(self):
        assert _infer_color("seal", "rubber") == "#1a1a1a"

    def test_glass_material(self):
        assert _infer_color("lens", "glass") == "#a8d8ea"

    def test_part_category_block_fallback(self):
        color = _infer_color("engine block", "")
        assert color == "#4a4e69"

    def test_part_category_shaft_fallback(self):
        color = _infer_color("drive shaft", "")
        assert color == "#6e7c8c"

    def test_part_category_fan_fallback(self):
        color = _infer_color("cooling fan", "")
        assert color == "#2c2f33"

    def test_completely_unknown_returns_default(self):
        color = _infer_color("widget xyz", "")
        assert color == "#607d8b"

    def test_returns_valid_hex_format(self):
        color = _infer_color("random part", "unknown material")
        assert color.startswith("#")
        assert len(color) == 7


# ─── Geometry Inference Tests ─────────────────────────────────────────────────

class TestInferGeometry:
    def test_piston_is_cylinder(self):
        geo = _infer_geometry("piston rod")
        assert geo["type"] == "cylinder"
        assert "radius" in geo

    def test_engine_block_is_box(self):
        geo = _infer_geometry("engine block")
        assert geo["type"] == "box"
        assert "size" in geo

    def test_crankshaft_is_cylinder(self):
        geo = _infer_geometry("crankshaft")
        assert geo["type"] == "cylinder"

    def test_sphere_part(self):
        geo = _infer_geometry("ball bearing")
        assert geo["type"] == "sphere"

    def test_fan_blade(self):
        geo = _infer_geometry("cooling fan blade")
        assert geo["type"] == "fan"
        assert "blades" in geo

    def test_gear_is_lathe(self):
        geo = _infer_geometry("timing gear")
        assert geo["type"] == "lathe"

    def test_gasket_is_torus(self):
        geo = _infer_geometry("head gasket")
        assert geo["type"] == "torus"

    def test_nozzle_is_cone(self):
        geo = _infer_geometry("fuel nozzle")
        assert geo["type"] == "cone"

    def test_unknown_defaults_to_box(self):
        geo = _infer_geometry("mystery widget 9000")
        assert geo["type"] == "box"

    def test_geometry_has_valid_dimensions(self):
        geo = _infer_geometry("cylinder")
        assert all(isinstance(v, (int, float)) for k, v in geo.items() if k != "type")


# ─── Gemini3DService Initialization Tests ─────────────────────────────────────

class TestGemini3DServiceInit:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        """Without API key, generate_3d_object must return None gracefully."""
        service = Gemini3DService(api_key="")
        result = await service.generate_3d_object("telescope", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_research_data_handled(self):
        """Empty research_data dict should not cause crash when key missing."""
        service = Gemini3DService(api_key="")
        result = await service.generate_3d_object("engine", {})
        assert result is None  # no key = no generation, no crash

    def test_api_key_set_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-from-env")
        service = Gemini3DService()
        assert service.api_key == "test-key-from-env"

    def test_explicit_api_key_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        service = Gemini3DService(api_key="explicit-key")
        assert service.api_key == "explicit-key"


# ─── Gemini3DService Generation Tests ─────────────────────────────────────────

class TestGemini3DServiceGeneration:
    @pytest.mark.asyncio
    async def test_valid_json_response_parsed(self):
        """Mock Gemini returning valid JSON — should return dict with components."""
        import json

        fake_response_data = {
            "id": "telescope",
            "name": "Telescope",
            "type": "optical_instrument",
            "summary": "An optical telescope.",
            "defaultView": "assembled",
            "model": {"kind": "procedural", "assetUrl": None},
            "components": [
                {
                    "id": "main_tube",
                    "name": "Main Tube",
                    "parentId": None,
                    "scaleLevel": "component",
                    "function": "Houses primary mirror",
                    "material": "Aluminum",
                    "riskIfRemoved": "Total collapse",
                    "position": [0, 0, 0],
                    "color": "#c0c5ce",
                    "geometry": {"type": "cylinder", "radius": 0.3, "depth": 1.0},
                    "children": [],
                    "microLevels": [],
                }
            ],
        }

        service = Gemini3DService(api_key="fake-key-for-mock")

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_response_data)
        mock_model.generate_content.return_value = mock_response

        service._model = mock_model  # inject mock

        result = await service.generate_3d_object(
            "telescope",
            {"title": "Telescope", "description": "Optical telescope", "details": ""},
        )

        assert result is not None
        assert result["name"] == "Telescope"
        assert len(result["components"]) == 1
        assert result["components"][0]["id"] == "main_tube"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self):
        """Gemini returning broken JSON must return None, not crash."""
        service = Gemini3DService(api_key="fake-key")

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is not JSON at all { broken"
        mock_model.generate_content.return_value = mock_response
        service._model = mock_model

        result = await service.generate_3d_object("engine", {"title": "Engine"})
        assert result is None

    @pytest.mark.asyncio
    async def test_markdown_fences_stripped(self):
        """Gemini sometimes wraps JSON in markdown — must be stripped."""
        import json

        fake_data = {
            "id": "car",
            "name": "Car",
            "type": "vehicle",
            "summary": "A car.",
            "defaultView": "assembled",
            "model": {"kind": "procedural", "assetUrl": None},
            "components": [],
        }

        service = Gemini3DService(api_key="fake-key")
        mock_model = MagicMock()
        mock_response = MagicMock()
        # Gemini sometimes adds ```json ... ``` wrapping
        mock_response.text = f"```json\n{json.dumps(fake_data)}\n```"
        mock_model.generate_content.return_value = mock_response
        service._model = mock_model

        result = await service.generate_3d_object("car", {})
        assert result is not None
        assert result["name"] == "Car"
