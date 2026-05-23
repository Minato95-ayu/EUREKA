"""
Gemini3DService - Uses Google Gemini AI to generate unique, accurate 3D model JSON
from Wikipedia research data. This replaces the generic Ollama fallback.

No API key needed for testing - uses Gemini's free tier via google-generativeai package.
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ─── Gemini colours / geometry knowledge base ─────────────────────────────────
MATERIAL_COLORS: Dict[str, str] = {
    "steel":        "#4a4e69",
    "cast iron":    "#3d3d3d",
    "iron":         "#3d3d3d",
    "aluminum":     "#c0c5ce",
    "aluminium":    "#c0c5ce",
    "copper":       "#b87333",
    "brass":        "#b5a642",
    "chrome":       "#d4d8dd",
    "titanium":     "#8c97a5",
    "carbon fiber": "#1c1c1c",
    "rubber":       "#1a1a1a",
    "plastic":      "#607d8b",
    "glass":        "#a8d8ea",
    "ceramic":      "#f0e5d8",
    "gold":         "#ffd700",
    "silver":       "#c0c0c0",
    "bronze":       "#cd7f32",
    "composite":    "#546e7a",
    "alloy":        "#78909c",
}

GEOMETRY_RULES: Dict[str, str] = {
    "engine block": "box",
    "block":        "box",
    "housing":      "box",
    "piston":       "cylinder",
    "cylinder":     "cylinder",
    "shaft":        "cylinder",
    "rod":          "cylinder",
    "tube":         "cylinder",
    "pipe":         "cylinder",
    "fan":          "fan",
    "blade":        "fan",
    "propeller":    "fan",
    "ball":         "sphere",
    "sphere":       "sphere",
    "dome":         "hemisphere",
    "ring":         "torus",
    "gasket":       "torus",
    "belt":         "torus",
    "gear":         "lathe",
    "flywheel":     "lathe",
    "pulley":       "lathe",
    "nozzle":       "cone",
    "cone":         "cone",
}


def _infer_color(name: str, material: str = "") -> str:
    combined = (name + " " + material).lower()
    for keyword, color in MATERIAL_COLORS.items():
        if keyword in combined:
            return color
    # Sane defaults by part category
    if any(k in combined for k in ("block", "case", "housing", "frame", "body")):
        return "#4a4e69"
    if any(k in combined for k in ("shaft", "rod", "bolt", "screw", "nut", "pin")):
        return "#6e7c8c"
    if any(k in combined for k in ("pipe", "tube", "hose")):
        return "#2d4a2d"
    if any(k in combined for k in ("cap", "cover", "lid", "seal")):
        return "#3a3a3a"
    if any(k in combined for k in ("fan", "propeller", "blade")):
        return "#2c2f33"
    return "#607d8b"


def _infer_geometry(name: str) -> Dict[str, Any]:
    nl = name.lower()
    for keyword, gtype in GEOMETRY_RULES.items():
        if keyword in nl:
            if gtype == "cylinder":
                return {"type": "cylinder", "radius": 0.2, "depth": 0.5}
            if gtype == "box":
                return {"type": "box", "size": [1.0, 0.5, 0.8]}
            if gtype == "sphere":
                return {"type": "sphere", "radius": 0.25}
            if gtype == "torus":
                return {"type": "torus", "radius": 0.35, "tube": 0.07}
            if gtype == "fan":
                return {"type": "fan", "radius": 0.5, "blades": 5}
            if gtype == "hemisphere":
                return {"type": "hemisphere", "radius": 0.3}
            if gtype == "cone":
                return {"type": "cone", "radius": 0.25, "depth": 0.6}
            if gtype == "lathe":
                return {"type": "lathe", "radius": 0.4, "depth": 0.25}
    return {"type": "box", "size": [0.5, 0.5, 0.5]}


class Gemini3DService:
    """
    Uses Google Gemini API to generate a structured, unique 3D component tree
    for any user-searched object, enriched with Wikipedia research data.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._genai = None
        self._model = None

    def _init_model(self):
        """Lazy-init the Gemini SDK."""
        if self._model:
            return True
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set – Gemini3DService disabled.")
            return False
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"temperature": 0.4, "max_output_tokens": 2048},
            )
            logger.info("Gemini 3D service initialised (gemini-1.5-flash).")
            return True
        except ImportError:
            logger.error("google-generativeai package not installed. Run: pip install google-generativeai")
            return False
        except Exception as e:
            logger.error(f"Failed to init Gemini: {e}")
            return False

    async def generate_3d_object(
        self,
        query: str,
        research_data: Dict[str, Any],
    ) -> Optional[Dict]:
        """
        Ask Gemini to produce a 3D component JSON for `query`, guided by research.
        Returns a dict suitable for ExplorableObject.model_validate() or None on failure.
        """
        if not self._init_model():
            return None

        title       = research_data.get("title", query)
        description = research_data.get("description", "")
        details     = research_data.get("details", "")

        prompt = f"""You are a 3D model architect. Generate a JSON object describing the physical components of a "{query}".

Real-world context from Wikipedia:
Title: {title}
Description: {description}
Details: {details[:400]}

STRICT RULES:
1. Return ONLY valid JSON — no markdown, no explanation.
2. Top-level keys: id, name, type, summary, defaultView, model, components
3. Each component has: id, name, parentId, scaleLevel, function, material, riskIfRemoved, position, color, geometry, children, microLevels
4. geometry.type must be one of: box, cylinder, sphere, torus, fan, cone, hemisphere, lathe
5. Create exactly 6 to 8 components. Root component has parentId null.
6. Use REAL colors: cast iron = #3d3d3d, aluminum = #c0c5ce, copper = #b87333, rubber = #1a1a1a, steel = #4a4e69
7. Use REAL-WORLD part names specific to a {query}. NOT generic names like "Left Terminal".
8. Positions must place parts in correct spatial relationships.
9. defaultView = "assembled", model = {{"kind": "procedural", "assetUrl": null}}

JSON schema example for ONE component:
{{
  "id": "engine_block",
  "name": "Engine Block",
  "parentId": null,
  "scaleLevel": "component",
  "function": "Central cast-iron housing for cylinders and crankshaft.",
  "material": "Cast Iron",
  "riskIfRemoved": "Total engine collapse.",
  "position": [0.0, 0.0, 0.0],
  "color": "#3d3d3d",
  "geometry": {{"type": "box", "size": [1.5, 0.9, 0.8]}},
  "children": ["cylinder_head", "crankshaft"],
  "microLevels": []
}}

Now generate the complete JSON for: {query}"""

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self._model.generate_content(prompt)
            )
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            # Ensure required top-level fields
            data.setdefault("id", query.lower().replace(" ", "_"))
            data.setdefault("name", title)
            data.setdefault("type", "mechanical_system")
            data.setdefault("summary", description[:200] or f"A {query}.")
            data.setdefault("defaultView", "assembled")
            data.setdefault("model", {"kind": "procedural", "assetUrl": None})

            # Post-process components: fill missing colors/geometry
            for comp in data.get("components", []):
                if not comp.get("color"):
                    comp["color"] = _infer_color(comp.get("name", ""), comp.get("material", ""))
                if not comp.get("geometry"):
                    comp["geometry"] = _infer_geometry(comp.get("name", ""))
                comp.setdefault("microLevels", [])
                comp.setdefault("children", [])
                comp.setdefault("scaleLevel", "component")

            logger.info(f"Gemini generated {len(data.get('components', []))} components for '{query}'")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON for '{query}': {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini generation failed for '{query}': {e}")
            return None
