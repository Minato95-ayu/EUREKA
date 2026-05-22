from app.agents.base_agent import BaseAgent
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ExplainerAgent(BaseAgent):
    """Explains scientific concepts clearly"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "Explainer")
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Explainer Agent. Your role is to make complex 
scientific concepts understandable to researchers and students.

Your expertise:
- Atomic structure and bonding
- Chemical reactions mechanisms
- Biological processes
- Physics principles
- Historical context of discoveries

When explaining:
1. Start with fundamental concepts
2. Build complexity gradually
3. Use analogies when helpful
4. Provide real-world examples
5. Connect to applications

Be clear, engaging, and accessible. Avoid jargon when possible, 
but define technical terms when necessary."""
    
    async def process(self, request: Dict[str, Any]) -> str:
        """Process explanation request"""
        
        question = request.get("question", "")
        context = request.get("context", {})
        
        context_str = self._build_context(context)
        
        prompt = f"""{context_str}

User Question: {question}

Provide a clear, engaging explanation that:
1. Addresses the question directly
2. Explains underlying principles
3. Uses analogies or examples
4. Connects to real-world applications
5. Suggests follow-up questions"""
        
        response = await self.generate_response(prompt)
        if not response or response.startswith("Error") or "Error generating response" in response:
            logger.info("Explainer LLM failed/offline. Using rule-based fallback.")
            response = self._get_fallback_response(question)
        else:
            logger.info(f"Explainer processed: {question[:50]}...")
        
        return response

    def _get_fallback_response(self, question: str) -> str:
        ctx = self._parse_context_from_message(question)
        
        # If there is a selected component
        if ctx["component"] != "unknown":
            return f"""**Scientific Explanation: {ctx['component']} ({ctx['object']})**

### Functional Role
The **{ctx['component']}** performs a critical operational role in the {ctx['object']}:
> *"{ctx['function']}"*

### Material Specifications & Properties
- **Primary Material:** {ctx['material']}
- This material is selected for its high structural integrity, specific weight/density ratios, and compatibility with the operating environment's thermal/stress requirements.

### System Dependability & Safety Criticality
- **Risk If Disrupted/Removed:** {ctx['risk_if_removed']}
- Removal or failure of this component triggers immediate system degradation or structural collapse due to loss of physical support, load distribution imbalances, or thermal runaway.

---
*Note: This explanation is running in EUREKA offline mode. Select other parts of the CAD model to query their metrics.*"""

        # General object-level explanation fallback
        question_lower = question.lower()
        if "engine" in question_lower or "car" in question_lower:
            return """**System Overview: Inline-4 Internal Combustion Engine**

The **Inline-4 Engine** is an internal combustion mechanical system. It utilizes four cylinders arranged in a straight line to execute the four-stroke Otto cycle (Intake, Compression, Power, Exhaust), converting chemical fuel energy into rotational mechanical drive.

### Core Component Breakdown
1. **Engine Block**: The foundational casting supporting cylinder bores, coolant passages, and oil lines.
2. **Cylinder Head**: Seals the cylinders and houses intake/exhaust valves and spark plugs.
3. **Oil Pan**: The lower fluid reservoir collecting engine lubricant.
4. **Crankshaft**: Converts the linear reciprocating force of pistons into rotational torque.
5. **Flywheel**: A heavy inertial disk smoothing out torque pulsations between combustion cycles.
6. **Pistons & Rods**: Pistons translate combustion pressure down cylinder bores, while connecting rods link them to the crank throws.
7. **Cooling Fan**: Regulates the block's thermal load via high-velocity airflow.

*Use the CAD viewport to select specific subcomponents for detailed micro-level material analysis.*"""

        elif "drone" in question_lower or "quadcopter" in question_lower:
            return """**System Overview: Quadcopter Drone**

A **Quadcopter Drone** is an unmanned multirotor aerial vehicle. Thrust and direction are governed by varying the rotational speed of four distinct brushless motor/propeller assemblies mounted on symmetrical support arms.

### Core Component Breakdown
1. **Carbon Frame Chassis**: A high-rigidity, low-mass center plate carrying batteries and electronics.
2. **Support Arms**: Structural extension arms positioning motors at optimal thrust radii.
3. **Brushless DC Motors**: High-speed, high-torque electric motors regulating propeller spin.
4. **Propellers**: Symmetrical airfoil blades designed to generate aerodynamic lift through differential pressure.

*Use the CAD viewport to inspect arm configurations and motor orientations.*"""

        elif "microscope" in question_lower or "scope" in question_lower:
            return """**System Overview: Compound Microscope**

A **Compound Microscope** is a high-precision optical instrument utilizing refractive glass lenses and an adjustable focus assembly to resolve microscopic specimens.

### Core Component Breakdown
1. **Microscope Base**: A heavy cast iron base stabilizing the assembly.
2. **Support Column**: A vertical rigid pillar aligning optical lenses and the stage.
3. **Specimen Stage**: Flat platform with clamping clips where specimen slides are mounted.
4. **Monocular Eyepiece**: Focus tube containing the primary magnifying glass elements.

*Use the CAD viewport to explore mechanical adjustments and optic pathways.*"""

        else:
            return f"""**System Overview: Scientific Apparatus**

This is an interactive CAD blueprint showing the structural components of the system.

### Primary Layout
- **Frame/Chassis:** Provides the foundational assembly load path.
- **Support Terminals:** Regulate power, signaling, and mechanical interconnects.

*Select individual components to display their functional definitions and physical properties.*"""


# Usage example
async def explain_concept(ollama_service, concept: str):
    agent = ExplainerAgent(ollama_service)
    request = {
        "question": f"Explain {concept}",
        "context": {"experiment": "Water Analysis"}
    }
    return await agent.process(request)
