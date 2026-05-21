# EUREKA Missing Features Build Plan

Last updated: May 21, 2026

## Goal

Build the missing core loop for EUREKA:

```text
Search -> 3D object -> select component -> ask ARIA -> modify -> simulate -> explain -> cite
```

The first target should be a focused demo object, not an infinite universe. Start with `car engine`, then add `rocket`, `human heart`, and `water molecule`.

## Research-Backed Technical Direction

- Use React Three Fiber pointer events for component picking because events include Three.js object, point, and distance data.
- Use Three.js `GLTFLoader` / React Three Fiber model loading for real model assets when available.
- Use FastAPI `APIRouter` modules for each major API area: objects, ARIA, simulations, research, experiments.
- Use FastAPI WebSockets for live ARIA/simulation streaming.
- Use MediaPipe Hand Landmarker or Gesture Recognizer for webcam gestures. Its output includes hand landmarks and world landmarks, which are enough for pinch, point, swipe, and two-hand gestures.
- Use RDKit for molecular properties, conformers, descriptors, and SMILES-based molecule data.
- Use ArXiv, PubMed/NCBI E-utilities, and OpenAlex APIs for legal research metadata and citations.
- Use BullMQ + Redis for automation and long-running research/simulation jobs.

## Phase 0: Stabilize Current Repo

### Missing

- Backend tests fail when environment variable `DEBUG=release` is present.
- Automation TypeScript build fails if dependencies are not installed.
- README and API docs claim more than the current app actually implements.
- Frontend has encoding artifacts in visible text.

### Build Steps

1. Make backend settings tolerant of `DEBUG=release` or document correct `.env`.
2. Add `.env.example` for backend, frontend, and automation.
3. Run backend tests with clean env.
4. Run `npm install` in `eureka-automation/`, then validate `npm run build`.
5. Fix broken README/API docs so they match real routes.
6. Replace broken UI symbols with ASCII text or proper icons.

### Done When

- `eureka-frontend`: `npm run build` passes.
- `eureka-backend`: `python -m pytest -q` passes.
- `eureka-automation`: `npm run build` passes.
- Docs do not overclaim production readiness.

## Phase 1: Object Search and Component Graph

### Missing

There is no real search-to-3D pipeline and no object/component schema.

### Backend Files To Add

- `eureka-backend/app/models/object_graph.py`
- `eureka-backend/app/services/object_library.py`
- `eureka-backend/app/api/objects.py`
- `eureka-backend/app/data/demo_objects/car_engine.json`

### Data Shape

```json
{
  "id": "car_engine",
  "name": "Car Engine",
  "type": "mechanical_system",
  "defaultView": "assembled",
  "model": {
    "kind": "procedural",
    "assetUrl": null
  },
  "components": [
    {
      "id": "piston",
      "name": "Piston",
      "parentId": "engine_block",
      "function": "Compresses air-fuel mixture and receives combustion force.",
      "material": "Aluminum alloy",
      "riskIfRemoved": "Engine loses compression and cannot produce useful power.",
      "children": []
    }
  ]
}
```

### API Steps

1. Add `GET /api/objects/search?q=car engine`.
2. Add `GET /api/objects/{object_id}`.
3. Add `GET /api/objects/{object_id}/components/{component_id}`.
4. Register object router in `main.py`.
5. Add tests for search, object lookup, and component lookup.

### Frontend Steps

1. Add search box state: `searchQuery`, `activeObject`, `selectedComponent`.
2. Replace static water molecule text with object search result.
3. Render demo car engine procedurally first using Three.js primitives.
4. Add clickable meshes with component IDs.
5. Show component hierarchy panel.

### Done When

User searches `car engine`, gets an engine scene, clicks `piston`, and the UI shows piston metadata.

## Phase 2: ARIA Context Brain

### Missing

ARIA is currently a generic multi-agent coordinator. It does not know selected object/component context.

### Backend Files To Add Or Change

- Add `eureka-backend/app/api/aria.py`
- Add `eureka-backend/app/services/aria_context.py`
- Improve `eureka-backend/app/agents/helper_agent.py`

### API Shape

```json
POST /api/aria/chat
{
  "message": "How does this part work?",
  "objectId": "car_engine",
  "componentId": "piston",
  "mode": "explain"
}
```

### Build Steps

1. Create ARIA request/response models.
2. Load object + component metadata before calling agents.
3. Replace keyword-only routing with intent detection:
   - explain
   - analyze
   - what_if
   - research
   - navigation
4. Return structured response:
   - answer
   - warnings
   - suggested_actions
   - citations
   - simulation_request if needed
5. Frontend should call `/api/aria/chat`, not only `/api/agents/process`.

### Done When

User selects piston and asks: `ARIA, explain this`. ARIA answers specifically about piston, not generic engine text.

## Phase 3: Recursive Zoom

### Missing

No object-to-component-to-molecule-to-atom navigation model exists.

### Data Model

Each component node should support:

```json
{
  "id": "piston",
  "scaleLevel": "component",
  "children": ["piston_ring", "wrist_pin"],
  "microLevels": [
    {
      "level": "material",
      "name": "Aluminum alloy",
      "next": "aluminum_crystal"
    },
    {
      "level": "atom",
      "name": "Aluminum atom"
    }
  ]
}
```

### Build Steps

1. Add `scaleLevel` to object graph: object, component, subcomponent, material, molecule, atom.
2. Add frontend breadcrumb: `Car Engine / Piston / Aluminum Alloy / Atom`.
3. Add zoom action:
   - mouse wheel or pinch zoom near selected component
   - `open component` voice command
4. Add lazy component loading:
   - object loads first
   - detailed child nodes load only when opened
5. Add transition animations between levels.

### Done When

User can move from engine view into piston view, then material/molecule/atom placeholder view.

## Phase 4: What-If Simulation

### Missing

Existing simulation engine is not connected to product actions like remove part, change material, or heat test.

### Backend Files To Add

- `eureka-backend/app/models/experiment.py`
- `eureka-backend/app/services/what_if_engine.py`
- `eureka-backend/app/api/experiments.py`

### First MVP Scenarios

- Remove cooling fan.
- Change piston material.
- Increase RPM.
- Reduce fuel input.

### API Shape

```json
POST /api/experiments/what-if
{
  "objectId": "car_engine",
  "componentId": "cooling_fan",
  "change": {
    "type": "remove_component"
  }
}
```

### Output Shape

```json
{
  "summary": "Removing the cooling fan increases heat risk.",
  "metrics": {
    "heat": "high",
    "fuelEfficiency": "unchanged",
    "speed": "unstable",
    "risk": "high"
  },
  "warnings": [
    "Engine overheating likely under load."
  ]
}
```

### Build Steps

1. Create rules-based what-if engine for demo objects.
2. Connect ARIA to what-if engine.
3. Show result cards and warnings in frontend.
4. Add experiment history.
5. Add undo/redo later.

### Done When

User says `Remove cooling fan and run heat simulation`, and EUREKA returns visible metrics + ARIA explanation.

## Phase 5: Research-Grounded Citations

### Missing

Research services exist, but ARIA does not reliably return source-backed citations inside the product loop.

### Sources

- ArXiv for physics, engineering-adjacent, math, AI, computation.
- PubMed/NCBI E-utilities for biology and medical topics.
- OpenAlex for broad scholarly metadata and citation graph.

### Backend Files To Add Or Improve

- `eureka-backend/app/services/research_retriever.py`
- `eureka-backend/app/services/citation_store.py`
- `eureka-backend/app/api/research.py`

### Build Steps

1. Convert user/component context into research query terms.
2. Query official APIs only.
3. Cache paper metadata in database.
4. Rank papers by title/abstract match, year, source, and component relevance.
5. Ask ARIA to answer with citations only from retrieved metadata.
6. Show citation cards in frontend.

### Done When

ARIA can answer an engine/heart/molecule question and show 2-5 source cards.

## Phase 6: Gesture and Voice Upgrade

### Missing

Current gesture support exists but is still basic and mixed into `App.tsx`.

### Frontend Files To Add

- `eureka-frontend/src/hooks/useVoiceCommands.ts`
- `eureka-frontend/src/hooks/useHandGestures.ts`
- `eureka-frontend/src/services/commandRouter.ts`

### Build Steps

1. Move voice recognition into a hook.
2. Move MediaPipe logic into a hook.
3. Map gestures to semantic commands:
   - pinch: zoom
   - point: select
   - fist: hold/reset
   - swipe: switch panel
   - two-hand spread: explode view
4. Add visible gesture confidence state.
5. Add command normalization for English/Hindi phrases.

### Done When

Voice and gesture logic is reusable, testable, and can control object/component actions.

## Phase 7: Automation and Research Jobs

### Missing

Automation scaffold exists, but it is not connected to a real dashboard or persistent job results.

### Build Steps

1. Install automation dependencies and validate TypeScript build.
2. Add job result persistence.
3. Add queue status endpoint in backend.
4. Add frontend automation panel that reads real queue stats.
5. Add PDF extraction only for legally accessible PDFs.
6. Add report generation for selected research topic.

### Done When

User enters a research topic, automation collects papers, queues analysis jobs, and shows report status in frontend.

## Phase 8: Cloud / Colab Runtime

### Missing

No Colab setup or cloud split exists yet.

### Build Steps

1. Create `colab/EUREKA_Backend_Runtime.ipynb`.
2. Add backend install/start cells.
3. Add Ollama or hosted model configuration.
4. Add ngrok/localtunnel instructions.
5. Add frontend `.env` support for remote API URL.
6. Add health check page.

### Done When

Weak laptop can run frontend locally while backend runs in Colab/cloud.

## Best Build Order

1. Stabilize tests and docs.
2. Build object search + car engine component graph.
3. Make 3D scene dynamic and clickable.
4. Make ARIA component-aware.
5. Add one what-if simulation.
6. Add citation-backed research answers.
7. Refactor voice/gesture into hooks.
8. Connect automation dashboard.
9. Add cloud/Colab runtime.

## First 7-Day Sprint

### Day 1

- Fix config/test issue.
- Fix docs mismatch.
- Create object schema.

### Day 2

- Add object search backend endpoints.
- Add car engine demo JSON.
- Add backend tests.

### Day 3

- Add frontend search service.
- Render car engine procedural scene.
- Add component click selection.

### Day 4

- Add ARIA `/api/aria/chat`.
- Inject selected component context.
- Connect frontend ARIA panel.

### Day 5

- Add what-if engine with remove cooling fan and change material scenarios.
- Show result metrics in frontend.

### Day 6

- Add research retriever skeleton.
- Connect ArXiv/PubMed/OpenAlex metadata search.
- Show citation cards.

### Day 7

- Clean UI, fix text/encoding, run builds/tests.
- Update `PROJECT_STATUS.md`.

## MVP Success Demo

The MVP is successful when this exact demo works:

1. User searches `car engine`.
2. EUREKA loads a 3D engine scene.
3. User clicks piston.
4. User asks `ARIA, how does this work?`
5. ARIA explains piston using object context.
6. User says `Remove cooling fan and run heat simulation`.
7. EUREKA shows heat/fuel/speed/risk metrics.
8. ARIA explains the risk and shows source cards.

