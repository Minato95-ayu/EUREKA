import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from app.agents.base_agent import BaseAgent
from app.models.object_graph import ExplorableObject, ObjectComponent, SimulationProperties, MicroLevel
from app.services.ollama_service import OllamaService
from app.config import get_settings

logger = logging.getLogger(__name__)

class ObjectArchitectAgent(BaseAgent):
    """Generates procedurally assembled, 3D-ready structured object graphs from keywords."""

    def __init__(self, ollama_service: OllamaService):
        super().__init__(ollama_service, "ObjectArchitect")
        self.settings = get_settings()
        self.cache_dir = Path(__file__).resolve().parents[1] / "data" / "generated_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_system_prompt(self) -> str:
        return """You are the EUREKA AI Object Architect.
Your task is to decompose any scientific, chemical, mechanical, or physical object requested by the user into a detailed, procedurally assemblable 3D representation.

You must output a strictly valid JSON document matching the schema described below. Do not output any conversational text, markdown formatting, or HTML. ONLY output raw JSON.

JSON SCHEMA:
{
  "id": "string (lowercase_snake_case_id of the object)",
  "name": "string (Title Case Name of the object)",
  "type": "string (one of: mechanical_system, molecular_system, optical_system, biological_system, chemical_system)",
  "summary": "string (brief 1-2 sentence description of the object)",
  "defaultView": "assembled",
  "model": {
    "kind": "procedural",
    "assetUrl": null
  },
  "components": [
    {
      "id": "string (lowercase_snake_case unique ID for the component)",
      "name": "string (readable component name)",
      "parentId": "string or null (ID of parent component, root component must be null)",
      "scaleLevel": "string (one of: object, component, subcomponent, material, molecule, atom)",
      "function": "string (description of the part's mechanical or scientific purpose)",
      "material": "string or null (material type, e.g. Carbon Fiber, Copper, Glass)",
      "riskIfRemoved": "string or null (physics consequence if this part is removed)",
      "position": [number, number, number] (3D offset [x, y, z] from origin or parent),
      "color": "string (hex color representation, e.g., #6f7f8f. Choose vibrant, material-themed colors)",
      "geometry": {
        "type": "box" | "cylinder" | "capsule" | "fan",
        "size": [number, number, number] (required ONLY if type is 'box' [width, height, depth]),
        "radius": number (required if type is 'cylinder', 'capsule', or 'fan'),
        "depth": number (required if type is 'cylinder' or 'capsule'),
        "blades": number (optional, integer for fan type),
        "rotation": [number, number, number] (optional, rotation angles in radians [rx, ry, rz])
      },
      "children": ["string"] (list of IDs of immediate child components),
      "microLevels": [
        {
          "level": "material" | "molecule" | "atom",
          "name": "string",
          "description": "string"
        }
      ],
      "simulationProperties": {
        "mass": number (estimated mass in kg),
        "heatGeneration": number (0.0 to 1.0 scale),
        "energyConsumption": number (0.0 to 1.0 scale)
      }
    }
  ]
}

PROCEDURAL DESIGN RULES:
1. Root component: You must design a single main structural component (e.g. chassis, frame, engine_block, central_nucleus) to act as the root. It MUST have "parentId": null and position [0.0, 0.0, 0.0].
2. Positional Coordinates: Estimate realistic, relative sizes and offsets.
   - Symmetrical Parts: Mirror positions on corresponding axes (e.g. left arm at [-1.0, 0, 0] and right arm at [1.0, 0, 0]).
   - Propellers/Fans: Position above their motors/mounts (e.g. motor at [1.0, 0.5, 0.0], propeller at [1.0, 0.7, 0.0]).
3. Hierarchy consistency: Ensure the graph is acyclic and fully connected. If part B's parentId is A, then A's "children" list MUST contain "B".
4. Sizes: Size parameters must be reasonable positive floats (e.g. sizes/depths between 0.05 and 5.0).
5. Colors: Do not use generic primaries. Use curated HSL-tailored hex values matching the material (e.g., carbon: #2c2f33, aluminum: #b2bec3, copper: #d27d2d, brass: #d4af37, steel: #7f8c8d, iron: #556270, polymer/black plastic: #1e272e, glass: #e0f2f1).
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

        # Fast Health Shortcut: if Ollama is offline, bypass LLM attempts
        if not await self.ollama.health_check():
            logger.info(f"Ollama is offline. Instantly serving fallback preset for query: '{query}'")
            fallback_obj = self.generate_fallback_object(query)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(fallback_obj.model_dump(by_alias=True), f, indent=2)
                logger.info(f"Cached fallback preset for offline use: '{query}'")
            except Exception as cache_err:
                logger.warning(f"Failed to cache fallback result: {cache_err}")
            return fallback_obj

        # 2. LLM Generation
        prompt = f"Decompose the following scientific/mechanical object into a 3D-ready assembly tree: '{query}'"
        
        try:
            logger.info(f"Requesting Ollama generation for query: '{query}'")
            raw_response = await self.ollama.generate(
                prompt=prompt,
                system=self.system_prompt,
                format="json",
                options={"temperature": self.settings.GENERATOR_TEMPERATURE}
            )
            
            # Parse raw response
            if not raw_response or raw_response.strip() == "Error generating response":
                raise ValueError("Ollama response empty or error flag returned")
                
            parsed_json = json.loads(raw_response.strip())
            
            # Apply procedural structure rules
            cleaned_json = self._apply_rule_engine(parsed_json, query)
            
            # Validate with Pydantic
            validated_obj = ExplorableObject.model_validate(cleaned_json)
            
            # Write to Cache
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(validated_obj.model_dump(by_alias=True), f, indent=2)
                logger.info(f"Successfully cached generation for: '{query}'")
            except Exception as cache_err:
                logger.warning(f"Failed to cache result: {cache_err}")
                
            return validated_obj
            
        except Exception as err:
            logger.error(f"Generation pipeline failed for '{query}': {err}. Triggering fallback...")
            fallback_obj = self.generate_fallback_object(query)
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(fallback_obj.model_dump(by_alias=True), f, indent=2)
                logger.info(f"Cached fallback preset after generation error: '{query}'")
            except Exception as cache_err:
                logger.warning(f"Failed to cache fallback result: {cache_err}")
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
            if gtype not in ["box", "cylinder", "capsule", "fan"]:
                geometry["type"] = "box"
                gtype = "box"
                
            if gtype == "box":
                size = geometry.get("size")
                if not isinstance(size, list) or len(size) != 3 or any(not isinstance(v, (int, float)) or v <= 0 for v in size):
                    geometry["size"] = [1.0, 1.0, 1.0]
            else:
                radius = geometry.get("radius")
                if not isinstance(radius, (int, float)) or radius <= 0:
                    geometry["radius"] = 0.5
                depth = geometry.get("depth")
                if not isinstance(depth, (int, float)) or depth <= 0:
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

    def generate_fallback_object(self, query: str) -> ExplorableObject:
        """Creates a beautiful pre-coded structural assembly when LLM fails or times out."""
        normalized = query.strip().lower()
        
        # --- DRONE PRESET ---
        if "drone" in normalized or "quad" in normalized or "copter" in normalized:
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
                ObjectComponent(
                    id="engine_block",
                    name="Engine Block",
                    parentId=None,
                    scaleLevel="component",
                    function="Central structural block housing cylinders, cooling channels, and crankshaft support.",
                    material="Cast Iron",
                    riskIfRemoved="Engine structure collapses; no housing for cylinders or oil flow.",
                    position=[0.0, 0.0, 0.0],
                    color="#556270",
                    geometry={"type": "box", "size": [2.2, 0.8, 1.0]},
                    children=["cylinder_head", "oil_pan", "crankshaft", "piston_1", "piston_2", "piston_3", "piston_4", "cooling_fan"],
                    simulationProperties=SimulationProperties(mass=80.0, heatGeneration=0.1, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="cylinder_head",
                    name="Cylinder Head",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Closes the top of the cylinders to form combustion chambers and houses valves.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Loss of compression; combustion cannot occur.",
                    position=[0.0, 0.5, 0.0],
                    color="#778899",
                    geometry={"type": "box", "size": [2.2, 0.2, 0.9]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=25.0, heatGeneration=0.05, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="oil_pan",
                    name="Oil Pan",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reservoir for engine oil and collects lubricating fluid under the block.",
                    material="Pressed Steel",
                    riskIfRemoved="Oil leaks immediately, causing severe engine seizure due to lack of lubrication.",
                    position=[0.0, -0.5, 0.0],
                    color="#2c3e50",
                    geometry={"type": "box", "size": [2.0, 0.2, 0.8]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=8.0, heatGeneration=0.01, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="crankshaft",
                    name="Crankshaft",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Converts linear piston motion into rotational force for the drivetrain.",
                    material="Forged Steel",
                    riskIfRemoved="Linear piston energy cannot be converted to mechanical drive.",
                    position=[0.0, -0.3, 0.0],
                    color="#a8b2c1",
                    geometry={"type": "cylinder", "radius": 0.1, "depth": 2.2, "rotation": [0.0, 0.0, 1.57]},
                    children=["flywheel"],
                    simulationProperties=SimulationProperties(mass=18.0, heatGeneration=0.15, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="flywheel",
                    name="Flywheel",
                    parentId="crankshaft",
                    scaleLevel="subcomponent",
                    function="Heavy disk storing rotational inertia to smooth out engine cycles.",
                    material="Cast Iron",
                    riskIfRemoved="Severe engine vibration and stalling between power strokes.",
                    position=[1.15, -0.3, 0.0],
                    color="#34495e",
                    geometry={"type": "cylinder", "radius": 0.45, "depth": 0.1, "rotation": [0.0, 0.0, 1.57]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=12.0, heatGeneration=0.02, energyConsumption=0.0)
                ),
                # Pistons
                ObjectComponent(
                    id="piston_1",
                    name="Piston 1",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 1 loses power and creates severe balance issues.",
                    position=[-0.75, 0.1, 0.0],
                    color="#dfe6e9",
                    geometry={"type": "cylinder", "radius": 0.22, "depth": 0.35},
                    children=["connecting_rod_1"],
                    simulationProperties=SimulationProperties(mass=0.8, heatGeneration=0.6, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_1",
                    name="Connecting Rod 1",
                    parentId="piston_1",
                    scaleLevel="subcomponent",
                    function="Connects piston 1 to the crankshaft, translating linear motion.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 1 motion is disconnected from the crankshaft.",
                    position=[-0.75, -0.15, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.05, "depth": 0.3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_2",
                    name="Piston 2",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 2 loses power.",
                    position=[-0.25, 0.1, 0.0],
                    color="#dfe6e9",
                    geometry={"type": "cylinder", "radius": 0.22, "depth": 0.35},
                    children=["connecting_rod_2"],
                    simulationProperties=SimulationProperties(mass=0.8, heatGeneration=0.6, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_2",
                    name="Connecting Rod 2",
                    parentId="piston_2",
                    scaleLevel="subcomponent",
                    function="Connects piston 2 to the crankshaft, translating linear motion.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 2 motion is disconnected.",
                    position=[-0.25, -0.15, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.05, "depth": 0.3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_3",
                    name="Piston 3",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 3 loses power.",
                    position=[0.25, 0.1, 0.0],
                    color="#dfe6e9",
                    geometry={"type": "cylinder", "radius": 0.22, "depth": 0.35},
                    children=["connecting_rod_3"],
                    simulationProperties=SimulationProperties(mass=0.8, heatGeneration=0.6, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_3",
                    name="Connecting Rod 3",
                    parentId="piston_3",
                    scaleLevel="subcomponent",
                    function="Connects piston 3 to the crankshaft, translating linear motion.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 3 motion is disconnected.",
                    position=[0.25, -0.15, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.05, "depth": 0.3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.08, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="piston_4",
                    name="Piston 4",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.",
                    material="Aluminum Alloy",
                    riskIfRemoved="Cylinder 4 loses power.",
                    position=[0.75, 0.1, 0.0],
                    color="#dfe6e9",
                    geometry={"type": "cylinder", "radius": 0.22, "depth": 0.35},
                    children=["connecting_rod_4"],
                    simulationProperties=SimulationProperties(mass=0.8, heatGeneration=0.6, energyConsumption=0.0)
                ),
                ObjectComponent(
                    id="connecting_rod_4",
                    name="Connecting Rod 4",
                    parentId="piston_4",
                    scaleLevel="subcomponent",
                    function="Connects piston 4 to the crankshaft, translating linear motion.",
                    material="Forged Steel",
                    riskIfRemoved="Piston 4 motion is disconnected.",
                    position=[0.75, -0.15, 0.0],
                    color="#7f8c8d",
                    geometry={"type": "cylinder", "radius": 0.05, "depth": 0.3},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.5, heatGeneration=0.08, energyConsumption=0.0)
                ),
                # Accessories
                ObjectComponent(
                    id="cooling_fan",
                    name="Cooling Fan",
                    parentId="engine_block",
                    scaleLevel="subcomponent",
                    function="Pulls cooling air through radiator to prevent overheating.",
                    material="Composite Polymer",
                    riskIfRemoved="Engine runs hot under load, high thermal seizure risk.",
                    position=[-1.25, 0.0, 0.0],
                    color="#2f3640",
                    geometry={"type": "fan", "radius": 0.5, "blades": 6, "rotation": [0.0, 0.0, 1.57]},
                    children=[],
                    simulationProperties=SimulationProperties(mass=1.5, heatGeneration=0.02, energyConsumption=0.1)
                )
            ]
            return ExplorableObject(
                id="car_engine",
                name="Inline-4 Car Engine",
                type="mechanical_system",
                summary="A detailed inline-4 internal combustion engine with engine block, oil pan, cylinder head, crankshaft, pistons, and radiator cooling fan.",
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

        # --- GENERIC DEFAULT ---
        else:
            name = query.title() if query else "Generic Core Component"
            components = [
                ObjectComponent(
                    id="core_frame",
                    name=f"{name} Core Frame",
                    parentId=None,
                    scaleLevel="component",
                    function="Main structural assembly support framework.",
                    material="Anodized Aluminum",
                    riskIfRemoved="Complete structural failure. System collapses.",
                    position=[0.0, 0.0, 0.0],
                    color="#4a5568",
                    geometry={"type": "box", "size": [1.5, 0.5, 1.5]},
                    children=["accessory_left", "accessory_right"],
                    simulationProperties=SimulationProperties(mass=2.0, heatGeneration=0.1, energyConsumption=0.05)
                ),
                ObjectComponent(
                    id="accessory_left",
                    name="Left Support Terminal",
                    parentId="core_frame",
                    scaleLevel="subcomponent",
                    function="Secondary connector terminal on the left hemisphere.",
                    material="Polymer Composite",
                    riskIfRemoved="Loss of peripheral connectivity on left channel.",
                    position=[-1.1, 0.0, 0.0],
                    color="#546de5",
                    geometry={"type": "cylinder", "radius": 0.25, "depth": 0.6},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.4, heatGeneration=0.2, energyConsumption=0.1)
                ),
                ObjectComponent(
                    id="accessory_right",
                    name="Right Support Terminal",
                    parentId="core_frame",
                    scaleLevel="subcomponent",
                    function="Secondary connector terminal on the right hemisphere.",
                    material="Polymer Composite",
                    riskIfRemoved="Loss of peripheral connectivity on right channel.",
                    position=[1.1, 0.0, 0.0],
                    color="#d27d2d",
                    geometry={"type": "cylinder", "radius": 0.25, "depth": 0.6},
                    children=[],
                    simulationProperties=SimulationProperties(mass=0.4, heatGeneration=0.2, energyConsumption=0.1)
                )
            ]
            return ExplorableObject(
                id=query.strip().lower().replace(" ", "_") if query else "generic_object",
                name=name,
                type="mechanical_system",
                summary=f"A default procedural blueprint for: {name}.",
                defaultView="assembled",
                model={"kind": "procedural", "assetUrl": None},
                components=components
            )
