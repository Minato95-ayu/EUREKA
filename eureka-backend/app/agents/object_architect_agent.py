import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from app.agents.base_agent import BaseAgent
from app.models.object_graph import ExplorableObject, ObjectComponent, SimulationProperties, MicroLevel
from app.services.ollama_service import OllamaService
from app.services.web_research_service import WebResearchService
from app.services.gemini_3d_service import Gemini3DService
from app.config import get_settings

logger = logging.getLogger(__name__)

class ObjectArchitectAgent(BaseAgent):
    """Generates procedurally assembled, 3D-ready structured object graphs from keywords."""

    def __init__(self, ollama_service: OllamaService):
        super().__init__(ollama_service, "ObjectArchitect")
        self.settings = get_settings()
        self.cache_dir = Path(__file__).resolve().parents[1] / "data" / "generated_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.research_service = WebResearchService()
        self.gemini_service = Gemini3DService()  # primary AI – uses GEMINI_API_KEY env var

    def _get_system_prompt(self, research_context: str = "") -> str:
        research_block = ""
        if research_context:
            research_block = f"""

REAL-WORLD RESEARCH DATA (use this to make your output physically accurate):
---
{research_context}
---
Use the research data above to determine correct materials, proportions, sub-parts, colors, and functions.
"""

        return f"""You are the EUREKA AI Object Architect — an expert mechanical/scientific engineer.
Your task is to decompose any object into a HIGHLY DETAILED, PHYSICALLY ACCURATE, procedurally assemblable 3D representation with 15-25 components for complex objects.

You must output a strictly valid JSON document matching the schema below. Do not output any conversational text, markdown formatting, or HTML. ONLY output raw JSON.
{research_block}
JSON SCHEMA:
{{
  "id": "string (lowercase_snake_case_id of the object)",
  "name": "string (Title Case Name of the object)",
  "type": "string (one of: mechanical_system, molecular_system, optical_system, biological_system, chemical_system)",
  "summary": "string (brief 1-2 sentence description of the object)",
  "defaultView": "assembled",
  "model": {{
    "kind": "procedural",
    "assetUrl": null
  }},
  "components": [
    {{
      "id": "string (lowercase_snake_case unique ID for the component)",
      "name": "string (readable component name)",
      "parentId": "string or null (ID of parent component, root component must be null)",
      "scaleLevel": "string (one of: object, component, subcomponent, material, molecule, atom)",
      "function": "string (description of the part's mechanical or scientific purpose)",
      "material": "string or null (material type, e.g. Carbon Fiber, Copper, Glass)",
      "riskIfRemoved": "string or null (physics consequence if this part is removed)",
      "position": [number, number, number] (3D offset [x, y, z] from origin or parent),
      "color": "string (hex color — MUST match the real-world material color)",
      "geometry": {{
        "type": "box" | "cylinder" | "capsule" | "fan" | "sphere" | "cone" | "torus" | "hemisphere" | "rounded_box" | "lathe" | "csg",
        ... type-specific parameters (see GEOMETRY TYPES below)
      }},
      "children": ["string"] (list of IDs of immediate child components),
      "microLevels": [
        {{
          "level": "material" | "molecule" | "atom",
          "name": "string",
          "description": "string"
        }}
      ],
      "simulationProperties": {{
        "mass": number (estimated mass in kg),
        "heatGeneration": number (0.0 to 1.0 scale),
        "energyConsumption": number (0.0 to 1.0 scale)
      }}
    }}
  ]
}}

GEOMETRY TYPES — choose the BEST shape for each real-world part:
  • box:         {{ "type": "box", "size": [w, h, d] }}  — blocks, plates, frames, housings
  • cylinder:    {{ "type": "cylinder", "radius": r, "depth": d }}  — shafts, rods, pistons, tubes, pipes
  • capsule:     {{ "type": "capsule", "radius": r, "depth": d }}  — rounded rods, handles, biological shapes
  • fan:         {{ "type": "fan", "radius": r, "blades": n }}  — propellers, impellers, turbines
  • sphere:      {{ "type": "sphere", "radius": r }}  — balls, bearings, knobs, spherical joints, atoms
  • cone:        {{ "type": "cone", "radius": r, "depth": d }}  — nozzles, tips, funnels, valve seats
  • torus:       {{ "type": "torus", "radius": r, "tube": t }}  — belts, O-rings, gaskets, seals, loops
  • hemisphere:  {{ "type": "hemisphere", "radius": r }}  — domes, caps, lens covers, rounded ends
  • rounded_box: {{ "type": "rounded_box", "size": [w, h, d], "radius": r }}  — enclosures, ECUs, rounded housings
  • lathe:       {{ "type": "lathe", "radius": r, "depth": d }}  — turned parts, pulleys, flanges
  • csg:         {{ "type": "csg", "base": {{ "type": "box", "size": [w,h,d] }}, "subtractions": [{{ "type": "cylinder", "radius": r, "depth": d, "position": [x,y,z], "rotation": [x,y,z] }}] }} — Carve physical holes out of shapes using CSG Booleans. Use for engine blocks (cylinder bores), vented covers, drilled plates.
  All types accept optional "rotation": [rx, ry, rz] in radians.

REAL-WORLD MATERIAL COLORS — you MUST use these exact hex colors:
  • Cast Iron:        #4a4a4f (dark gray with blue undertone)
  • Aluminum / Alloy: #c0c5ce (light silver-gray)
  • Steel / Forged:   #71797e (medium steel gray)
  • Copper:           #b87333 (warm copper-orange)
  • Brass:            #b5a642 (yellow-gold)
  • Chrome / Plated:  #e8e8e8 (bright near-white silver)
  • Rubber / Neoprene:#1a1a1a (near black)
  • Carbon Fiber:     #2c2f33 (dark charcoal)
  • Glass / Lens:     #d4f1f9 (pale cyan, semi-transparent appearance)
  • Ceramic:          #f5f0e8 (warm off-white)
  • Gold:             #ffd700 (bright gold)
  • Titanium:         #878681 (warm gray)
  • Polymer / Plastic:#3a3a3c (dark gray)
  • Stainless Steel:  #c8c8c8 (bright gray)
  • Bronze:           #cd7f32 (warm dark gold)
  • Nickel:           #a0a0a0 (neutral silver)
  • Zinc:             #bac4cb (cool light gray)
  • Wood:             #8b6914 (warm brown)
  • Fabric / Canvas:  #c2b280 (khaki tan)
  • Red Paint:        #c0392b (automotive red)
  • Blue Paint:       #2980b9 (automotive blue)
  • White Paint:      #ecf0f1 (automotive white)
  • Black Paint:      #1c1c1e (glossy black)

REAL-WORLD PROPORTIONS — use actual physical dimensions scaled to 3D units:
  • 1 unit in 3D = approximately 1 meter in the real world (so 60cm = 0.6 units)
  • A car engine block is roughly 0.6m long × 0.35m tall × 0.4m deep → size [0.6, 0.35, 0.4]
  • A piston is roughly 8-10cm diameter × 7cm tall → cylinder radius 0.045, depth 0.07
  • A crankshaft is roughly 3-5cm diameter × 45cm long → cylinder radius 0.02, depth 0.45
  • A bolt head is roughly 1cm × 1cm → cylinder radius 0.005, depth 0.01
  • Keep parts in correct proportion relative to each other!

PROCEDURAL DESIGN RULES:
1. Root component: Design a single main structural component (e.g. chassis, frame, engine_block) as root with "parentId": null and position [0.0, 0.0, 0.0].
2. DETAIL LEVEL: Create EXACTLY 5 to 8 components max. DO NOT generate more than 8 components. Keep it fast!
3. Positional Coordinates: Estimate realistic relative offsets. Mirror symmetrical parts. Stack parts correctly.
4. Hierarchy: Ensure acyclic, fully connected graph. If B's parentId is A, then A's children MUST contain B.
5. GEOMETRY MATCHING: Use the correct geometry type for each part:
   - Pistons, shafts, rods, tubes → cylinder
   - Belts, O-rings, gaskets → torus
   - Ball bearings, spherical joints → sphere
   - Nozzles, funnels → cone
   - Domes, caps → hemisphere
   - ECU boxes, smooth housings → rounded_box
   - Pulleys, turned parts → lathe
   - Flat plates, blocks → box
   - Propellers, fans → fan
   - Parts with holes or drilled cutouts (engine block, vented housing, disc brakes) → csg
6. Colors: MUST match the real-world material. Do NOT use random or generic colors.
"""

    def _get_cache_path(self, query: str) -> Path:
        normalized = query.strip().lower()
        query_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{query_hash}.json"

    async def process(self, request: Dict[str, Any]) -> str:
        """Required by BaseAgent interface. Returns JSON string of ExplorableObject."""
        query = request.get("message", "").strip()
        if not query:
            return json.dumps(self.generate_fallback_object("generic").model_dump(by_alias=True))
        
        obj = await self.generate_object(query)
        return json.dumps(obj.model_dump(by_alias=True))

    async def generate_object(self, query: str) -> ExplorableObject:
        """Checks cache, executes LLM request, applies rule cleaning, and returns validated model."""
        cache_path = self._get_cache_path(query)
        
        # 1. Cache Lookup
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                logger.info(f"Cache hit for query: '{query}'")
                return ExplorableObject.model_validate(payload)
            except Exception as e:
                logger.warning(f"Cache read error for '{query}': {e}. Regenerating...")

        # 2. Web Research for real-world context (moved above offline check)
        research_data = {}
        research_context = ""
        try:
            research_data = await self.research_service.research_object(query)
            if research_data:
                research_context = f"Object: {research_data.get('title', query)}\n"
                if research_data.get('description'):
                    research_context += f"Description: {research_data['description']}\n"
                if research_data.get('details'):
                    research_context += f"Details: {research_data['details']}\n"
                logger.info(f"Wikipedia research enriched prompt for: '{query}'")
            else:
                logger.info(f"No Wikipedia data found for '{query}', proceeding without research context")
        except Exception as research_err:
            logger.warning(f"Web research failed for '{query}': {research_err}. Proceeding without.")

        # Fast Health Shortcut: if Ollama is offline, bypass LLM attempts
        if not await self.ollama.health_check():
            logger.info(f"Ollama is offline. Instantly serving smart fallback preset for query: '{query}'")
            fallback_obj = self.generate_fallback_object(query, research_data)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(fallback_obj.model_dump(by_alias=True), f, indent=2)
                logger.info(f"Cached fallback preset for offline use: '{query}'")
            except Exception as cache_err:
                logger.warning(f"Failed to cache fallback result: {cache_err}")
            return fallback_obj

        # 3-A. Try Gemini AI (primary – fast, smart, internet-aware)
        try:
            logger.info(f"[Gemini] Attempting primary AI generation for: '{query}'")
            gemini_result = await self.gemini_service.generate_3d_object(query, research_data)
            if gemini_result:
                cleaned_json = self._apply_rule_engine(gemini_result, query)
                validated_obj = ExplorableObject.model_validate(cleaned_json)
                try:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump(validated_obj.model_dump(by_alias=True), f, indent=2)
                except Exception:
                    pass
                logger.info(f"[Gemini] Successfully generated {len(validated_obj.components)} components for '{query}'")
                return validated_obj
            else:
                logger.info("[Gemini] No result (API key not set?). Falling back to Ollama.")
        except Exception as gemini_err:
            logger.warning(f"[Gemini] Failed: {gemini_err}. Trying Ollama...")

        # 3-B. Try local Ollama (secondary – requires local model)
        if not await self.ollama.health_check():
            logger.info(f"Ollama also offline. Serving smart Wikipedia fallback for: '{query}'")
            fallback_obj = self.generate_fallback_object(query, research_data)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(fallback_obj.model_dump(by_alias=True), f, indent=2)
            except Exception:
                pass
            return fallback_obj

        # 3-C. Ollama as secondary LLM
        system_prompt = self._get_system_prompt(research_context=research_context)
        prompt = f"Decompose the following scientific/mechanical object into a physically accurate 3D-ready assembly tree with 6-8 components: '{query}'"
        try:
            logger.info(f"[Ollama] Requesting generation for query: '{query}'")
            raw_response = await self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                format="json",
                options={"temperature": self.settings.GENERATOR_TEMPERATURE}
            )
            if not raw_response or raw_response.strip() == "Error generating response":
                raise ValueError("Ollama response empty or error flag returned")
            parsed_json = json.loads(raw_response.strip())
            cleaned_json = self._apply_rule_engine(parsed_json, query)
            validated_obj = ExplorableObject.model_validate(cleaned_json)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(validated_obj.model_dump(by_alias=True), f, indent=2)
            except Exception:
                pass
            return validated_obj
        except Exception as err:
            logger.error(f"[Ollama] Also failed for '{query}': {err}. Serving Wikipedia smart fallback...")
            fallback_obj = self.generate_fallback_object(query, research_data)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(fallback_obj.model_dump(by_alias=True), f, indent=2)
            except Exception:
                pass
            return fallback_obj

    def _apply_rule_engine(self, data: dict, query: str) -> dict:
        """Enforces structural rules, parent-child integrity, and coordinate validity."""
        if not isinstance(data, dict):
            raise ValueError("Input data for rules engine must be a dictionary")
            
        # Ensure root fields exist
        data.setdefault("id", query.strip().lower().replace(" ", "_"))
        data.setdefault("name", query.strip().title())
        data.setdefault("type", "mechanical_system")
        data.setdefault("summary", f"A procedurally generated {query}.")
        data.setdefault("defaultView", "assembled")
        data.setdefault("model", {"kind": "procedural", "assetUrl": None})
        
        components = data.get("components", [])
        if not isinstance(components, list) or len(components) == 0:
            # Inject a simple single-root component if empty
            components = [{
                "id": "core_body",
                "name": "Core Body",
                "parentId": None,
                "scaleLevel": "component",
                "function": f"The main body of the {query}.",
                "material": "Composite structure",
                "riskIfRemoved": "System disintegrates without core support.",
                "position": [0.0, 0.0, 0.0],
                "color": "#6f7f8f",
                "geometry": {"type": "box", "size": [1.0, 1.0, 1.0]},
                "children": [],
                "simulationProperties": {"mass": 1.0, "heatGeneration": 0.1, "energyConsumption": 0.1}
            }]
            data["components"] = components
            
        # 1. Identify root and clean parents
        has_root = False
        components_map = {c.get("id"): c for c in components if c.get("id")}
        
        for c in components:
            cid = c.get("id")
            # Enforce lowercase snake_case ID
            if cid:
                c["id"] = cid.lower().replace(" ", "_")
            else:
                c["id"] = "part_" + str(components.index(c))
                
            # Parent consistency check
            pid = c.get("parentId")
            if pid:
                c["parentId"] = pid.lower().replace(" ", "_")
                # If parent doesn't exist in components, make this part a root
                if c["parentId"] not in components_map:
                    c["parentId"] = None
            
            if c.get("parentId") is None:
                if not has_root:
                    has_root = True
                    # Force root to center coordinates
                    c["position"] = [0.0, 0.0, 0.0]
                else:
                    # Only one root allowed. Make subsequent orphan nodes child of the first root
                    first_root_id = next((x["id"] for x in components if x.get("parentId") is None), None)
                    c["parentId"] = first_root_id

            # Clean geometry structures
            geometry = c.setdefault("geometry", {})
            gtype = geometry.get("type", "box")
            valid_types = ["box", "cylinder", "capsule", "fan", "sphere", "cone", "torus", "hemisphere", "rounded_box", "lathe"]
            if gtype not in valid_types:
                geometry["type"] = "box"
                gtype = "box"
                
            if gtype == "box":
                size = geometry.get("size")
                if not isinstance(size, list) or len(size) != 3 or any(not isinstance(v, (int, float)) or v <= 0 for v in size):
                    geometry["size"] = [1.0, 1.0, 1.0]
            elif gtype == "rounded_box":
                size = geometry.get("size")
                if not isinstance(size, list) or len(size) != 3 or any(not isinstance(v, (int, float)) or v <= 0 for v in size):
                    geometry["size"] = [1.0, 1.0, 1.0]
                radius = geometry.get("radius")
                if not isinstance(radius, (int, float)) or radius <= 0:
                    geometry["radius"] = 0.05
            elif gtype == "sphere" or gtype == "hemisphere":
                radius = geometry.get("radius")
                if not isinstance(radius, (int, float)) or radius <= 0:
                    geometry["radius"] = 0.5
            elif gtype == "torus":
                radius = geometry.get("radius")
                if not isinstance(radius, (int, float)) or radius <= 0:
                    geometry["radius"] = 0.5
                tube = geometry.get("tube")
                if not isinstance(tube, (int, float)) or tube <= 0:
                    geometry["tube"] = 0.1
            else:
                # cylinder, capsule, fan, cone, lathe — all need radius + depth
                radius = geometry.get("radius")
                if not isinstance(radius, (int, float)) or radius <= 0:
                    geometry["radius"] = 0.5
                depth = geometry.get("depth")
                if gtype not in ["fan"] and (not isinstance(depth, (int, float)) or depth <= 0):
                    geometry["depth"] = 1.0
                if gtype == "fan":
                    geometry.setdefault("blades", 4)
            
            # Position NaN cleanup
            pos = c.get("position", [0.0, 0.0, 0.0])
            if not isinstance(pos, list) or len(pos) != 3 or any(not isinstance(v, (int, float)) or v != v for v in pos):
                c["position"] = [0.0, 0.0, 0.0]
                
            # Default properties
            c.setdefault("scaleLevel", "component")
            c.setdefault("color", "#a8b2c1")
            c.setdefault("function", "Supporting system component.")
            c.setdefault("children", [])
            c.setdefault("microLevels", [])
            
            # Simulation properties alias mapping
            sim_props = c.setdefault("simulationProperties", {})
            sim_props.setdefault("mass", 1.0)
            sim_props.setdefault("heatGeneration", 0.0)
            sim_props.setdefault("energyConsumption", 0.0)

        # 2. Reset children arrays and rebuild them properly to guarantee link integrity
        for c in components:
            c["children"] = []
            
        for c in components:
            pid = c.get("parentId")
            if pid:
                parent_node = next((node for node in components if node["id"] == pid), None)
                if parent_node:
                    parent_node["children"].append(c["id"])

        data["components"] = components
        return data

    def generate_fallback_object(self, query: str, research_data: dict = None) -> ExplorableObject:
        """Creates a beautiful pre-coded structural assembly when LLM fails or times out."""
        normalized = query.strip().lower()
        
        # --- AIRPLANE TURBOFAN ENGINE PRESET ---
        if "airplane" in normalized or "jet" in normalized or "turbofan" in normalized or "aircraft" in normalized or "aviation" in normalized:
            components = [
                ObjectComponent(
                    id="central_shaft",
                    name="Central Shaft",
                    parentId=None,
                    scaleLevel="component",
                    function="Central main shaft transmitting rotational torque from the turbines at the back to the fan and compressors at the front.",
                    material="Titanium Alloy",
                    riskIfRemoved="Total mechanical lock; compressor/fan cannot spin, leading to zero thrust and engine seizure.",
                    position=[0.0, 0.0, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.15, "depth": 3.6, "rotation": [0.0, 0.0, 1.5708]},
                    children=["intake_fan", "lp_compressor", "hp_compressor", "combustion_chamber", "hp_turbine", "lp_turbine", "exhaust_cone", "fan_casing", "engine_stand"],
                    microLevels=[
                        MicroLevel(level="material", name="Titanium crystal structure", description="Alpha-beta titanium alloy offering high tensile strength, toughness, and corrosion resistance at elevated temperatures.")
                    ],
                    simulationProperties=SimulationProperties(mass=120.0, heatGeneration=0.05, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="intake_fan",
                    name="Titanium Intake Fan",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Large front fan drawing in massive volumes of air, providing the bulk of thrust through the bypass duct.",
                    material="Titanium Alloy",
                    riskIfRemoved="Total loss of bypass thrust (80%+ of engine power) and no airflow to core.",
                    position=[-1.7, 0.0, 0.0],
                    color="#00b0ff",
                    geometry={"type": "fan", "radius": 1.4, "blades": 24, "rotation": [0.0, 0.0, 1.5708]},
                    children=["nose_cone"],
                    simulationProperties=SimulationProperties(mass=85.0, heatGeneration=0.02, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="nose_cone",
                    name="Nose Cone Spinner",
                    parentId="intake_fan",
                    scaleLevel="subcomponent",
                    function="Aerodynamic nose cone that diverts incoming air smoothly into the fan and compressor, and sheds ice.",
                    material="Composite Materials",
                    riskIfRemoved="Extreme aerodynamic drag, ice accumulation, and air turbulence leading to engine surge.",
                    position=[-1.85, 0.0, 0.0],
                    color="#1a1a1a",
                    geometry={"type": "cone", "radius": 0.35, "depth": 0.6, "rotation": [0.0, 0.0, -1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=12.0, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="lp_compressor",
                    name="Low-Pressure Compressor",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="First compression stage raising air pressure and temperature before it enters the high-pressure section.",
                    material="Titanium",
                    riskIfRemoved="Loss of initial compression, leading to immediate stall and engine failure.",
                    position=[-1.0, 0.0, 0.0],
                    color="#2ecc71",
                    geometry={"type": "cylinder", "radius": 0.8, "depth": 0.6, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=45.0, heatGeneration=0.1, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="hp_compressor",
                    name="High-Pressure Compressor",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Final compressor stage compressing air to extremely high pressure before combustion.",
                    material="Nickel Alloy",
                    riskIfRemoved="Engine cannot maintain self-sustaining combustion due to lack of compression.",
                    position=[-0.4, 0.0, 0.0],
                    color="#8eff1e",
                    geometry={"type": "cylinder", "radius": 0.65, "depth": 0.6, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=60.0, heatGeneration=0.25, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="combustion_chamber",
                    name="Combustion Chamber",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Area where fuel is injected, mixed with compressed air, and ignited to create hot, high-velocity gas.",
                    material="Ceramic Matrix Composite",
                    riskIfRemoved="No combustion possible; engine produces zero energy and stops.",
                    position=[0.2, 0.0, 0.0],
                    color="#e67e22",
                    geometry={"type": "cylinder", "radius": 0.7, "depth": 0.6, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=40.0, heatGeneration=0.9, energyConsumption=0.05)
                ),
                ObjectComponent(
                    id="hp_turbine",
                    name="High-Pressure Turbine",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Extracts energy from hot gas flow to drive the high-pressure compressor stage via outer shaft.",
                    material="Single-Crystal Nickel Superalloy",
                    riskIfRemoved="High-pressure compressor stops rotating; engine ceases operation immediately.",
                    position=[0.8, 0.0, 0.0],
                    color="#f1c40f",
                    geometry={"type": "cylinder", "radius": 0.75, "depth": 0.4, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=55.0, heatGeneration=0.8, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="lp_turbine",
                    name="Low-Pressure Turbine",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Extracts remaining gas energy to drive the main intake fan and low-pressure compressor.",
                    material="Nickel Alloy",
                    riskIfRemoved="Intake fan stops spinning; engine loses virtually all thrust.",
                    position=[1.3, 0.0, 0.0],
                    color="#e74c3c",
                    geometry={"type": "cylinder", "radius": 0.85, "depth": 0.5, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=75.0, heatGeneration=0.6, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="exhaust_cone",
                    name="Exhaust Nozzle Cone",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Channels exhaust gas flow to maximize velocity and direct the thrust vector.",
                    material="Inconel Alloy",
                    riskIfRemoved="Thrust efficiency drops dramatically; exhaust gases disperse unevenly.",
                    position=[1.75, 0.0, 0.0],
                    color="#d35400",
                    geometry={"type": "cone", "radius": 0.4, "depth": 0.6, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=30.0, heatGeneration=0.7, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="fan_casing",
                    name="Outer Fan Casing",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Surrounds fan blades to contain blade fragments in case of failure and duct incoming air.",
                    material="Kevlar & Aluminum",
                    riskIfRemoved="Critical safety risk: fan blade out event would destroy the aircraft wing/fuselage.",
                    position=[-1.2, 0.0, 0.0],
                    color="#3f51b5",
                    geometry={"type": "torus", "radius": 1.45, "tube": 0.08, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=150.0, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="engine_stand",
                    name="Structural Display Stand",
                    parentId="central_shaft",
                    scaleLevel="subcomponent",
                    function="Heavy display stand supporting the engine assembly for research and presentation.",
                    material="Structural Steel",
                    riskIfRemoved="Engine falls to the ground; cannot be operated or inspected.",
                    position=[0.0, -1.2, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "box", "size": [2.4, 0.2, 1.2]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=180.0, heatGeneration=0.0, energyConsumption=0.0)
                )
            ]
            return ExplorableObject(
                id="airplane_engine",
                name="Aviation Turbofan Engine",
                type="mechanical_system",
                summary="A high-bypass turbofan aircraft engine. Key components include the front fan, low-pressure/high-pressure compressors, combustion chamber, high-pressure/low-pressure turbines, exhaust nozzle, and structural stand.",
                defaultView="assembled",
                model={"kind": "procedural", "assetUrl": None},
                components=components
            )

        # --- DRONE PRESET ---
        elif "drone" in normalized or "quad" in normalized or "copter" in normalized:
            components = [
                ObjectComponent(
                    id="chassis",
                    name="Carbon Frame Chassis",
                    parentId=None,
                    scaleLevel="component",
                    function="Central frame plate housing flight controllers, electronics, and power distribution.",
                    material="Carbon Fiber",
                    riskIfRemoved="Total structural disintegration. Components cannot mount.",
                    position=[0.0, 0.0, 0.0],
                    color="#2c2f33",
                    geometry={"type": "box", "size": [1.4, 0.15, 1.4]},
                    children=["arm_1", "arm_2", "arm_3", "arm_4"],
                    microLevels=[
                        MicroLevel(level="material", name="Carbon fiber weave", description="Hexagonal crystalline carbon strands providing massive rigidity and low weight.")
                    ],
                    simulationProperties=SimulationProperties(mass=1.2, heatGeneration=0.05, energyConsumption=0.0)
                ),
                # Front-Left Arm
                ObjectComponent(
                    id="arm_1",
                    name="Front-Left Arm",
                    parentId="chassis",
                    scaleLevel="subcomponent",
                    function="Rigid support arm connecting chassis to front-left motor.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Propeller drops, asymmetric thrust causes immediate tumble.",
                    position=[-0.8, 0.0, 0.8],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.08, "depth": 0.8, "rotation": [0.0, 0.0, 1.57]},
                    children=["motor_1"],
                    simulationProperties=SimulationProperties(mass=0.18, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="motor_1",
                    name="Front-Left Motor",
                    parentId="arm_1",
                    scaleLevel="subcomponent",
                    function="Brushless DC motor generating torque for propeller spin.",
                    material="Neodymium Magnets & Copper",
                    riskIfRemoved="Propeller ceases rotation, causing yaw spin and drop.",
                    position=[-1.2, 0.15, 1.2],
                    color="#2c3e50",
                    geometry={"type": "cylinder", "radius": 0.14, "depth": 0.22},
                    children=["prop_1"],
                    simulationProperties=SimulationProperties(mass=0.22, heatGeneration=0.55, energyConsumption=0.45)
                ),
                ObjectComponent(
                    id="prop_1",
                    name="Front-Left Propeller",
                    parentId="motor_1",
                    scaleLevel="subcomponent",
                    function="Aerodynamic blades rotating to create pressure difference for lift.",
                    material="Polyester Polymer",
                    riskIfRemoved="No lift generation on Front-Left quadrant.",
                    position=[-1.2, 0.3, 1.2],
                    color="#1e272e",
                    geometry={"type": "fan", "radius": 0.44, "blades": 3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.04, heatGeneration=0.0, energyConsumption=0.0)
                ),
                # Front-Right Arm
                ObjectComponent(
                    id="arm_2",
                    name="Front-Right Arm",
                    parentId="chassis",
                    scaleLevel="subcomponent",
                    function="Rigid support arm connecting chassis to front-right motor.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Loss of front-right thrust leads to immediate roll crash.",
                    position=[0.8, 0.0, 0.8],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.08, "depth": 0.8, "rotation": [0.0, 0.0, 1.57]},
                    children=["motor_2"],
                    simulationProperties=SimulationProperties(mass=0.18, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="motor_2",
                    name="Front-Right Motor",
                    parentId="arm_2",
                    scaleLevel="subcomponent",
                    function="Brushless DC motor generating torque for propeller spin.",
                    material="Neodymium Magnets & Copper",
                    riskIfRemoved="Motor failure leads to instant crash.",
                    position=[1.2, 0.15, 1.2],
                    color="#2c3e50",
                    geometry={"type": "cylinder", "radius": 0.14, "depth": 0.22},
                    children=["prop_2"],
                    simulationProperties=SimulationProperties(mass=0.22, heatGeneration=0.55, energyConsumption=0.45)
                ),
                ObjectComponent(
                    id="prop_2",
                    name="Front-Right Propeller",
                    parentId="motor_2",
                    scaleLevel="subcomponent",
                    function="Aerodynamic blades rotating to create pressure difference for lift.",
                    material="Polyester Polymer",
                    riskIfRemoved="No lift generation on Front-Right quadrant.",
                    position=[1.2, 0.3, 1.2],
                    color="#1e272e",
                    geometry={"type": "fan", "radius": 0.44, "blades": 3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.04, heatGeneration=0.0, energyConsumption=0.0)
                ),
                # Back-Left Arm
                ObjectComponent(
                    id="arm_3",
                    name="Back-Left Arm",
                    parentId="chassis",
                    scaleLevel="subcomponent",
                    function="Rigid support arm connecting chassis to back-left motor.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Back-left motor drops, causing pitch tilt backwards.",
                    position=[-0.8, 0.0, -0.8],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.08, "depth": 0.8, "rotation": [0.0, 0.0, 1.57]},
                    children=["motor_3"],
                    simulationProperties=SimulationProperties(mass=0.18, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="motor_3",
                    name="Back-Left Motor",
                    parentId="arm_3",
                    scaleLevel="subcomponent",
                    function="Brushless DC motor generating torque for propeller spin.",
                    material="Neodymium Magnets & Copper",
                    riskIfRemoved="Motor failure results in total loss of control.",
                    position=[-1.2, 0.15, -1.2],
                    color="#2c3e50",
                    geometry={"type": "cylinder", "radius": 0.14, "depth": 0.22},
                    children=["prop_3"],
                    simulationProperties=SimulationProperties(mass=0.22, heatGeneration=0.55, energyConsumption=0.45)
                ),
                ObjectComponent(
                    id="prop_3",
                    name="Back-Left Propeller",
                    parentId="motor_3",
                    scaleLevel="subcomponent",
                    function="Aerodynamic blades rotating to create pressure difference for lift.",
                    material="Polyester Polymer",
                    riskIfRemoved="No lift generation on Back-Left quadrant.",
                    position=[-1.2, 0.3, -1.2],
                    color="#1e272e",
                    geometry={"type": "fan", "radius": 0.44, "blades": 3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.04, heatGeneration=0.0, energyConsumption=0.0)
                ),
                # Back-Right Arm
                ObjectComponent(
                    id="arm_4",
                    name="Back-Right Arm",
                    parentId="chassis",
                    scaleLevel="subcomponent",
                    function="Rigid support arm connecting chassis to back-right motor.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Back-right motor falls off, ending flight capability.",
                    position=[0.8, 0.0, -0.8],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.08, "depth": 0.8, "rotation": [0.0, 0.0, 1.57]},
                    children=["motor_4"],
                    simulationProperties=SimulationProperties(mass=0.18, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="motor_4",
                    name="Back-Right Motor",
                    parentId="arm_4",
                    scaleLevel="subcomponent",
                    function="Brushless DC motor generating torque for propeller spin.",
                    material="Neodymium Magnets & Copper",
                    riskIfRemoved="Motor failure terminates flight.",
                    position=[1.2, 0.15, -1.2],
                    color="#2c3e50",
                    geometry={"type": "cylinder", "radius": 0.14, "depth": 0.22},
                    children=["prop_4"],
                    simulationProperties=SimulationProperties(mass=0.22, heatGeneration=0.55, energyConsumption=0.45)
                ),
                ObjectComponent(
                    id="prop_4",
                    name="Back-Right Propeller",
                    parentId="motor_4",
                    scaleLevel="subcomponent",
                    function="Aerodynamic blades rotating to create pressure difference for lift.",
                    material="Polyester Polymer",
                    riskIfRemoved="No lift generation on Back-Right quadrant.",
                    position=[1.2, 0.3, -1.2],
                    color="#1e272e",
                    geometry={"type": "fan", "radius": 0.44, "blades": 3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.04, heatGeneration=0.0, energyConsumption=0.0)
                )
            ]
            return ExplorableObject(
                id="drone",
                name="Quadcopter Drone",
                type="mechanical_system",
                summary="A procedural fallback model of a standard quadcopter drone with 4 arms, brushless motors, and aerofoil propellers.",
                defaultView="assembled",
                model={"kind": "procedural", "assetUrl": None},
                components=components
            )
            
        # --- CAR ENGINE PRESET ---
        elif "engine" in normalized or "car" in normalized or "motor" in normalized:
            components = [
                # --- MAIN BLOCK ---
                ObjectComponent(
                    id="engine_block",
                    name="Engine Block",
                    parentId=None,
                    scaleLevel="component",
                    function="Primary cast-iron block housing 4 cylinder bores, water jackets, and crankcase. The structural backbone of the entire engine.",
                    material="Cast Iron",
                    riskIfRemoved="Total engine failure — no structure to contain combustion or support rotating assembly.",
                    position=[0.0, 0.0, 0.0],
                    color="#4a4a4f",
                    geometry={"type": "box", "size": [0.6, 0.35, 0.4]},
                    children=["cylinder_head", "oil_pan", "crankshaft", "piston_1", "piston_2", "piston_3", "piston_4",
                              "timing_belt", "water_pump", "alternator", "cooling_fan", "intake_manifold", "exhaust_manifold",
                              "thermostat_housing", "oil_filter", "starter_motor", "engine_mount_left", "engine_mount_right"],
                    microLevels=[
                        MicroLevel(level="material", name="Gray cast iron", description="Pearlitic gray iron with graphite flakes providing vibration damping and wear resistance.")
                    ],
                    simulationProperties=SimulationProperties(mass=45.0, heatGeneration=0.1, energyConsumption=0.0)
                ),
                # --- CYLINDER HEAD ---
                ObjectComponent(
                    id="cylinder_head",
                    name="Cylinder Head",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Aluminum casting closing the top of cylinder bores, containing combustion chambers, intake/exhaust ports, valve guides, and spark plug wells.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Complete loss of compression in all cylinders — no combustion possible.",
                    position=[0.0, 0.22, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "box", "size": [0.6, 0.1, 0.38]},
                    children=["valve_cover", "head_gasket"],
                    simulationProperties=SimulationProperties(mass=14.0, heatGeneration=0.3, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="valve_cover",
                    name="Valve Cover",
                    parentId="cylinder_head",
                    scaleLevel="subcomponent",
                    function="Stamped aluminum cover sealing the top of the cylinder head, protecting camshaft and valve springs from debris.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Oil leaks from top end; valve train exposed to contamination.",
                    position=[0.0, 0.30, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "rounded_box", "size": [0.58, 0.06, 0.35], "radius": 0.02},
                    children=[],
                    simulationProperties=SimulationProperties(mass=2.5, heatGeneration=0.02, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="head_gasket",
                    name="Head Gasket",
                    parentId="cylinder_head",
                    scaleLevel="subcomponent",
                    function="Multi-layer steel gasket sealing the joint between block and head, containing combustion pressure, coolant, and oil passages.",
                    material="Multi-Layer Steel",
                    riskIfRemoved="Blown head gasket: coolant mixes with oil, compression lost, catastrophic overheating.",
                    position=[0.0, 0.175, 0.0],
                    color="#71797e",
                    geometry={"type": "box", "size": [0.58, 0.003, 0.38]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.3, heatGeneration=0.0, energyConsumption=0.0)
                ),
                # --- OIL PAN ---
                ObjectComponent(
                    id="oil_pan",
                    name="Oil Pan",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Pressed steel sump collecting and storing engine oil. Contains oil pickup tube and drain plug.",
                    material="Pressed Steel",
                    riskIfRemoved="Total oil loss — engine seizes within minutes from lack of lubrication.",
                    position=[0.0, -0.25, 0.0],
                    color="#71797e",
                    geometry={"type": "box", "size": [0.55, 0.12, 0.35]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=4.5, heatGeneration=0.01, energyConsumption=0.0)
                ),
                # --- CRANKSHAFT & FLYWHEEL ---
                ObjectComponent(
                    id="crankshaft",
                    name="Crankshaft",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Forged steel rotating shaft converting linear piston motion into rotational torque via offset crank throws.",
                    material="Forged Steel",
                    riskIfRemoved="No rotational output — pistons move but produce no usable torque.",
                    position=[0.0, -0.12, 0.0],
                    color="#71797e",
                    geometry={"type": "cylinder", "radius": 0.025, "depth": 0.55, "rotation": [0.0, 0.0, 1.5708]},
                    children=["flywheel", "crankshaft_pulley"],
                    simulationProperties=SimulationProperties(mass=12.0, heatGeneration=0.15, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="flywheel",
                    name="Flywheel",
                    parentId="crankshaft",
                    scaleLevel="subcomponent",
                    function="Heavy cast-iron disc bolted to crankshaft rear, storing rotational inertia to smooth power delivery between combustion strokes.",
                    material="Cast Iron",
                    riskIfRemoved="Severe engine vibration, stalling at idle, impossible clutch engagement.",
                    position=[0.32, -0.12, 0.0],
                    color="#4a4a4f",
                    geometry={"type": "cylinder", "radius": 0.15, "depth": 0.025, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=8.0, heatGeneration=0.02, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="crankshaft_pulley",
                    name="Crankshaft Pulley",
                    parentId="crankshaft",
                    scaleLevel="subcomponent",
                    function="Harmonic balancer and drive pulley at crankshaft front, driving accessory belt system.",
                    material="Cast Iron",
                    riskIfRemoved="No drive for alternator, water pump, or A/C. Accessory systems fail.",
                    position=[-0.32, -0.12, 0.0],
                    color="#4a4a4f",
                    geometry={"type": "lathe", "radius": 0.08, "depth": 0.03, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=2.5, heatGeneration=0.01, energyConsumption=0.0)
                ),
                # --- PISTONS & CONNECTING RODS ---
                ObjectComponent(
                    id="piston_1",
                    name="Piston 1",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Forged aluminum piston reciprocating in cylinder bore 1, compressing air-fuel mixture and transmitting combustion force.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 1 dead — 25% power loss, severe vibration imbalance.",
                    position=[-0.2, 0.08, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.044, "depth": 0.065},
                    children=["connecting_rod_1"],
                    simulationProperties=SimulationProperties(mass=0.35, heatGeneration=0.7, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_1",
                    name="Connecting Rod 1",
                    parentId="piston_1",
                    scaleLevel="subcomponent",
                    function="Forged steel rod linking piston 1 to crankshaft crank throw, converting linear reciprocation to rotation.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 1 disconnected from crankshaft — thrown rod destroys engine.",
                    position=[-0.2, -0.04, 0.0],
                    color="#71797e",
                    geometry={"type": "capsule", "radius": 0.012, "depth": 0.14},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.45, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_2",
                    name="Piston 2",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Forged aluminum piston reciprocating in cylinder bore 2.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 2 dead — severe imbalance and 25% power loss.",
                    position=[-0.07, 0.08, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.044, "depth": 0.065},
                    children=["connecting_rod_2"],
                    simulationProperties=SimulationProperties(mass=0.35, heatGeneration=0.7, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_2",
                    name="Connecting Rod 2",
                    parentId="piston_2",
                    scaleLevel="subcomponent",
                    function="Forged steel rod linking piston 2 to crankshaft.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 2 disconnected — catastrophic engine damage.",
                    position=[-0.07, -0.04, 0.0],
                    color="#71797e",
                    geometry={"type": "capsule", "radius": 0.012, "depth": 0.14},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.45, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_3",
                    name="Piston 3",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Forged aluminum piston reciprocating in cylinder bore 3.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 3 dead.",
                    position=[0.07, 0.08, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.044, "depth": 0.065},
                    children=["connecting_rod_3"],
                    simulationProperties=SimulationProperties(mass=0.35, heatGeneration=0.7, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_3",
                    name="Connecting Rod 3",
                    parentId="piston_3",
                    scaleLevel="subcomponent",
                    function="Forged steel rod linking piston 3 to crankshaft.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 3 disconnected.",
                    position=[0.07, -0.04, 0.0],
                    color="#71797e",
                    geometry={"type": "capsule", "radius": 0.012, "depth": 0.14},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.45, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_4",
                    name="Piston 4",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Forged aluminum piston reciprocating in cylinder bore 4.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 4 dead.",
                    position=[0.2, 0.08, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.044, "depth": 0.065},
                    children=["connecting_rod_4"],
                    simulationProperties=SimulationProperties(mass=0.35, heatGeneration=0.7, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_4",
                    name="Connecting Rod 4",
                    parentId="piston_4",
                    scaleLevel="subcomponent",
                    function="Forged steel rod linking piston 4 to crankshaft.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 4 disconnected.",
                    position=[0.2, -0.04, 0.0],
                    color="#71797e",
                    geometry={"type": "capsule", "radius": 0.012, "depth": 0.14},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.45, heatGeneration=0.08, energyConsumption=0.0)
                ),
                # --- TIMING & ACCESSORIES ---
                ObjectComponent(
                    id="timing_belt",
                    name="Timing Belt",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reinforced rubber belt synchronizing crankshaft and camshaft rotation, ensuring valves open/close at correct piston positions.",
                    material="Reinforced Rubber",
                    riskIfRemoved="Valve timing lost — pistons strike open valves, bending them (interference engine).",
                    position=[-0.33, 0.05, 0.0],
                    color="#1a1a1a",
                    geometry={"type": "torus", "radius": 0.12, "tube": 0.012, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.3, heatGeneration=0.03, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="water_pump",
                    name="Water Pump",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Centrifugal impeller pump circulating coolant through block water jackets, head, and radiator.",
                    material="Aluminum Alloy",
                    riskIfRemoved="No coolant circulation — engine overheats rapidly, head gasket failure.",
                    position=[-0.35, 0.0, 0.15],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.06, "depth": 0.05, "rotation": [1.5708, 0.0, 0.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=1.8, heatGeneration=0.02, energyConsumption=0.05)
                ),
                ObjectComponent(
                    id="alternator",
                    name="Alternator",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Belt-driven generator converting mechanical rotation to electrical power for battery charging and vehicle electronics.",
                    material="Aluminum with Copper Windings",
                    riskIfRemoved="No electrical generation — battery drains, ignition and fuel injection fail.",
                    position=[0.0, 0.05, 0.28],
                    color="#c0c5ce",
                    geometry={"type": "cylinder", "radius": 0.07, "depth": 0.1, "rotation": [1.5708, 0.0, 0.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=5.5, heatGeneration=0.2, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="cooling_fan",
                    name="Cooling Fan",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Engine-driven or electric fan pulling ambient air through radiator core to reject combustion heat.",
                    material="Glass-Filled Nylon",
                    riskIfRemoved="Insufficient airflow at low speed — engine overheats in traffic.",
                    position=[0.0, 0.08, -0.28],
                    color="#3a3a3c",
                    geometry={"type": "fan", "radius": 0.18, "blades": 7, "rotation": [1.5708, 0.0, 0.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.9, heatGeneration=0.02, energyConsumption=0.08)
                ),
                ObjectComponent(
                    id="intake_manifold",
                    name="Intake Manifold",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Cast aluminum plenum distributing filtered air (or air-fuel mixture) evenly to all 4 cylinder intake ports.",
                    material="Cast Aluminum",
                    riskIfRemoved="No air delivery to cylinders — engine cannot run.",
                    position=[0.0, 0.15, 0.25],
                    color="#c0c5ce",
                    geometry={"type": "rounded_box", "size": [0.5, 0.08, 0.1], "radius": 0.02},
                    children=[],
                    simulationProperties=SimulationProperties(mass=4.0, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="exhaust_manifold",
                    name="Exhaust Manifold",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Cast iron manifold collecting exhaust gases from all 4 cylinders and routing them to the catalytic converter and exhaust system.",
                    material="Cast Iron",
                    riskIfRemoved="Exhaust gases vent into engine bay — toxic fumes, loss of back-pressure.",
                    position=[0.0, 0.1, -0.25],
                    color="#4a4a4f",
                    geometry={"type": "rounded_box", "size": [0.5, 0.08, 0.08], "radius": 0.015},
                    children=[],
                    simulationProperties=SimulationProperties(mass=8.0, heatGeneration=0.8, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="thermostat_housing",
                    name="Thermostat Housing",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Aluminum housing containing the thermostat valve that regulates coolant flow based on engine temperature.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Uncontrolled coolant flow — engine runs too cold or overheats.",
                    position=[0.28, 0.18, 0.0],
                    color="#c0c5ce",
                    geometry={"type": "hemisphere", "radius": 0.04},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.6, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="oil_filter",
                    name="Oil Filter",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Spin-on canister filter trapping metal particles, carbon, and contaminants from circulating engine oil.",
                    material="Steel Canister with Paper Media",
                    riskIfRemoved="Unfiltered oil circulates — accelerated bearing and cylinder wall wear.",
                    position=[0.2, -0.18, 0.22],
                    color="#1c1c1e",
                    geometry={"type": "cylinder", "radius": 0.04, "depth": 0.1, "rotation": [1.5708, 0.0, 0.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.4, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="starter_motor",
                    name="Starter Motor",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="High-torque DC electric motor with Bendix gear engaging flywheel ring gear to crank engine for starting.",
                    material="Steel and Copper Windings",
                    riskIfRemoved="Cannot crank engine — vehicle will not start.",
                    position=[0.3, -0.15, -0.1],
                    color="#71797e",
                    geometry={"type": "cylinder", "radius": 0.04, "depth": 0.15, "rotation": [0.0, 0.0, 1.5708]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=3.5, heatGeneration=0.4, energyConsumption=0.8)
                ),
                # --- ENGINE MOUNTS ---
                ObjectComponent(
                    id="engine_mount_left",
                    name="Left Engine Mount",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Rubber-bonded steel mount isolating engine vibrations from vehicle chassis on left side.",
                    material="Rubber bonded to Steel",
                    riskIfRemoved="Engine vibration transfers directly to chassis — severe NVH, potential drivetrain misalignment.",
                    position=[-0.32, -0.1, 0.0],
                    color="#1a1a1a",
                    geometry={"type": "cylinder", "radius": 0.04, "depth": 0.05},
                    children=[],
                    simulationProperties=SimulationProperties(mass=1.2, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="engine_mount_right",
                    name="Right Engine Mount",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Rubber-bonded steel mount isolating engine vibrations from vehicle chassis on right side.",
                    material="Rubber bonded to Steel",
                    riskIfRemoved="Asymmetric mounting — engine shifts under torque, belt slippage.",
                    position=[0.32, -0.1, 0.0],
                    color="#1a1a1a",
                    geometry={"type": "cylinder", "radius": 0.04, "depth": 0.05},
                    children=[],
                    simulationProperties=SimulationProperties(mass=1.2, heatGeneration=0.0, energyConsumption=0.0)
                ),
            ]
            return ExplorableObject(
                id="car_engine",
                name="Inline-4 Car Engine",
                type="mechanical_system",
                summary="A highly detailed inline-4 internal combustion engine with 25 components including engine block, cylinder head with valve cover and gasket, oil pan, crankshaft with flywheel and pulley, 4 pistons with connecting rods, timing belt, water pump, alternator, cooling fan, intake and exhaust manifolds, thermostat, oil filter, starter motor, and engine mounts — all with real-world materials, colors, and proportions.",
                defaultView="assembled",
                model={"kind": "procedural", "assetUrl": None},
                components=components
            )

        # --- MICROSCOPE PRESET ---
        elif "microscope" in normalized or "scope" in normalized:
            components = [
                ObjectComponent(
                    id="microscope_base",
                    name="Microscope Base",
                    parentId=None,
                    scaleLevel="component",
                    function="Heavy stabilizing stand for optical components.",
                    material="Cast Iron",
                    riskIfRemoved="Microscope becomes unstable and tips over easily.",
                    position=[0.0, -1.0, 0.0],
                    color="#34495e",
                    geometry={"type": "box", "size": [1.5, 0.2, 1.5]},
                    children=["stand_column"],
                    simulationProperties=SimulationProperties(mass=3.5, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="stand_column",
                    name="Support Column",
                    parentId="microscope_base",
                    scaleLevel="component",
                    function="Rigid column supporting stage, lenses, and light module.",
                    material="Steel Alloy",
                    riskIfRemoved="No structure to hold lenses or stage. Operations fail.",
                    position=[0.0, 0.0, -0.4],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.12, "depth": 1.6},
                    children=["specimen_stage", "eyepiece"],
                    simulationProperties=SimulationProperties(mass=1.8, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="specimen_stage",
                    name="Specimen Stage",
                    parentId="stand_column",
                    scaleLevel="subcomponent",
                    function="Flat platform holding slide with stage clips for adjustment.",
                    material="Anodized Aluminum",
                    riskIfRemoved="Nowhere to place sample slides. Cannot inspect objects.",
                    position=[0.0, -0.1, 0.2],
                    color="#2c3e50",
                    geometry={"type": "box", "size": [1.0, 0.08, 1.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.0, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="eyepiece",
                    name="Monocular Eyepiece",
                    parentId="stand_column",
                    scaleLevel="subcomponent",
                    function="Viewing tube containing secondary magnification lenses.",
                    material="Brass & Glass Lenses",
                    riskIfRemoved="Light cannot reach user's eye. Inspection becomes impossible.",
                    position=[0.0, 0.8, 0.1],
                    color="#d4af37",
                    geometry={"type": "cylinder", "radius": 0.16, "depth": 0.5, "rotation": [0.35, 0.0, 0.0]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.4, heatGeneration=0.0, energyConsumption=0.0)
                )
            ]
            return ExplorableObject(
                id="microscope",
                name="Compound Microscope",
                type="optical_system",
                summary="Procedural optical instrument layout with base stability, steel framing, a focus stage, and brass viewing eyepiece.",
                defaultView="assembled",
                model={"kind": "procedural", "assetUrl": None},
                components=components
            )

        # --- DYNAMIC WIKIPEDIA PROCEDURAL FALLBACK ---
        else:
            name = query.title() if query else "Generic Object"
            summary = f"A procedural blueprint for: {name}."
            image_url = None
            
            if research_data:
                name = research_data.get('title', name)
                summary = research_data.get('description', '') or research_data.get('details', summary)[:150]
                image_url = research_data.get('image_url')
                
            components = [
                ObjectComponent(
                    id="core_base",
                    name=f"{name} Main Base",
                    parentId=None,
                    scaleLevel="component",
                    function=f"The primary housing and structural foundation of the {name}.",
                    material="Hardened Alloy",
                    riskIfRemoved="Total structural failure.",
                    position=[0.0, 0.0, 0.0],
                    color="#34495e",
                    geometry={"type": "box", "size": [1.8, 0.6, 1.2]},
                    children=["top_housing", "front_sensor"],
                    simulationProperties=SimulationProperties(mass=5.0, heatGeneration=0.1, energyConsumption=0.1)
                ),
                ObjectComponent(
                    id="top_housing",
                    name="Upper Housing Module",
                    parentId="core_base",
                    scaleLevel="subcomponent",
                    function="Contains the primary operational mechanics.",
                    material="Aluminum",
                    riskIfRemoved="Loss of primary capability.",
                    position=[0.0, 0.5, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.4, "depth": 0.4, "rotation": [0, 0, 1.57]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=1.5, heatGeneration=0.2, energyConsumption=0.3)
                ),
                ObjectComponent(
                    id="front_sensor",
                    name="Forward Interface",
                    parentId="core_base",
                    scaleLevel="subcomponent",
                    function="Front-facing component for environmental interaction.",
                    material="Glass and Steel",
                    riskIfRemoved="Blindness or lack of input.",
                    position=[0.0, 0.0, 0.7],
                    color="#3498db",
                    geometry={"type": "sphere", "radius": 0.3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.05, energyConsumption=0.1)
                )
            ]
            
            model_info = {"kind": "procedural", "assetUrl": None}
            if image_url:
                model_info["assetUrl"] = image_url
                
            return ExplorableObject(
                id=query.strip().lower().replace(" ", "_") if query else "generic_object",
                name=name,
                type="dynamic_system",
                summary=summary,
                defaultView="assembled",
                model=model_info,
                components=components
            )
