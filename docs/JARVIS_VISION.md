# EUREKA JARVIS-Style Lab Vision

## Vision

EUREKA is an AI-powered 3D experimental laboratory inspired by a JARVIS-like workflow. A user should be able to search for an object, explore it in 3D, zoom from complete object down to internal parts and atomic structure, manipulate components, run what-if simulations, and ask ARIA for explanations, predictions, and research-backed guidance.

ARIA stands for AI Research and Innovation Assistant.

## Product Goals

- Make complex scientific and engineering systems explorable through interactive 3D.
- Combine search, simulation, research, and AI explanation into one lab workflow.
- Support weak local hardware by moving heavy AI and simulation tasks to cloud or Colab runtimes.
- Support natural interaction through chat, voice, and hand gestures.
- Keep answers grounded in scientific formulas, simulations, and cited research sources.

## Core User Flows

### Search and Visualize

1. User searches for an object, such as "car engine", "Saturn V rocket", "human heart", or "water molecule".
2. ARIA starts a loading conversation and requests object/model data from the backend.
3. Backend resolves the object into a structured model package.
4. Frontend renders the object in the 3D viewport.
5. ARIA summarizes the object and suggests useful explorations.

### Recursive Exploration

1. User zooms, selects, or asks for a component.
2. Frontend updates the selected node in the component hierarchy.
3. Backend loads more detailed component metadata or geometry.
4. Frontend transitions into the selected level.
5. ARIA explains the current level in simple language.

Example hierarchy:

```text
Car
-> Engine
-> Piston
-> Valve
-> Steel alloy structure
-> Molecules
-> Atoms
```

### Modify and Simulate

1. User asks "What happens if I remove this piston?"
2. Frontend sends the selected component and requested change.
3. Backend creates a simulation scenario.
4. Simulation engine estimates the outcome.
5. ARIA explains the result and cites supporting research when available.
6. Frontend displays visual changes, charts, and warnings.

### Research and Learn

1. User asks a conceptual question.
2. ARIA identifies relevant domain, component, formulas, and research terms.
3. Backend retrieves trusted papers or cached summaries.
4. ARIA answers with a practical explanation and source list.
5. Frontend shows citations, summaries, and related concepts.

## ARIA Capabilities

ARIA should eventually support:

- English and Hindi commands.
- Voice input through the browser Web Speech API.
- Voice output through browser speech synthesis.
- Context-aware explanation based on selected object/component.
- What-if prediction based on simulation services.
- Research lookup through reliable APIs such as ArXiv and PubMed.
- Proactive suggestions for next experiments.

ARIA should be conversational, concise, helpful, and scientific. It can feel JARVIS-like without pretending that uncertain simulation estimates are proven facts.

## 3D Visualization Requirements

- React + Three.js / React Three Fiber viewport.
- Object search bar and active object state.
- Component hierarchy panel.
- Smooth orbit, pan, zoom, isolate, and reset controls.
- Recursive zoom model for object-to-atom exploration.
- Lazy loading of detailed geometry and metadata.
- Highlighting, labels, and selected-component overlays.
- Simulation result overlays and graph panels.

## Gesture Requirements

Use MediaPipe hand tracking in the frontend.

Initial gesture command set:

| Gesture | Action |
| --- | --- |
| Pinch in/out | Zoom |
| Open palm drag | Rotate or pan |
| Point | Select component |
| Two-hand spread | Explode or expand view |
| Closed fist | Reset or hold selection |

Gesture UX should include clear feedback so the user knows what the system recognized.

## Simulation Requirements

The simulation layer should grow in stages.

### Current feasible MVP

- Particle movement.
- Basic force and energy calculation.
- RDKit molecular properties.
- Simple reaction feasibility estimation.
- What-if explanation generation.

### Future advanced simulation

- Stress analysis.
- Heat transfer.
- Fluid dynamics.
- Combustion approximation.
- Biological flow simulation.
- Material substitution effects.

Advanced simulation should be implemented through specialized engines or service integrations, not only through LLM text generation.

## Research Requirements

Preferred source order:

1. Cached internal knowledge and simulation context.
2. ArXiv API for physics, math, engineering-adjacent papers.
3. PubMed API for biology and medical topics.
4. Other sources only when they are reliable and legally accessible.

Google Scholar scraping should be treated carefully because it can be unreliable and may violate site restrictions. The safer first version should focus on official APIs and citation metadata sources.

## Cloud Runtime Strategy

The user's laptop should run:

- React frontend.
- WebGL/Three.js rendering.
- MediaPipe hand tracking.
- Voice input/output.

Cloud or Colab should run:

- FastAPI backend.
- ARIA LLM service.
- RAG/research retrieval.
- Heavy simulation jobs.
- Future model-generation jobs.

For early development, local Docker Compose can run the full stack. For weak-GPU use, the backend can be exposed from Colab through ngrok while the frontend points to that public API URL.

## MVP Scope

The first strong MVP should avoid trying to generate every possible 3D object automatically. Instead, it should support a small set of impressive demo objects with structured component data:

- Car engine.
- Rocket.
- Human heart.
- Water molecule.

MVP success flow:

1. Search "car engine".
2. See a 3D engine-style scene.
3. Select piston, crankshaft, valves, or spark plug.
4. Ask ARIA how the selected component works.
5. Run one what-if scenario.
6. See a visual change, result summary, and source-backed explanation.

## Key Engineering Principle

Build the JARVIS feeling through a complete interaction loop first:

```text
Search -> visualize -> select -> ask -> simulate -> explain -> cite
```

Once that loop works, improve model generation, simulation fidelity, and research depth incrementally.
