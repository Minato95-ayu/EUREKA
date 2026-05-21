# EUREKA Architecture

## System Overview

EUREKA follows a modular, microservice-ready architecture with clear separation between frontend, backend, and infrastructure layers.

## Components

### Frontend Layer
- **React 19 + TypeScript** — Component-based UI
- **Three.js / React Three Fiber** — 3D rendering and interaction
- **MediaPipe** — Hand gesture recognition
- **WebSocket Client** — Real-time communication

### Backend Layer
- **FastAPI** — Async REST API framework
- **Multi-Agent System** — 5 specialized AI agents coordinated by a Helper agent
- **Simulation Engine** — Physics (Coulomb, Van der Waals) and Chemistry (RDKit) engines
- **WebSocket Server** — Real-time bidirectional communication

### Data Layer
- **PostgreSQL 15** — Primary relational database with pgvector support
- **Redis 7** — Caching and session management
- **SQLAlchemy** — ORM with async support

### AI Layer
- **Ollama** — Local LLM runtime (Llama 3)
- **Agent Manager** — Routes queries, manages context, caches responses (MD5 hashing)

### Infrastructure Layer
- **Docker** — Containerization
- **Kubernetes** — Orchestration with HPA auto-scaling (3-10 pods)
- **Nginx** — Reverse proxy with TLS, rate limiting, WebSocket support
- **GitHub Actions** — CI/CD pipeline (test → build → deploy)
- **Prometheus + ELK** — Monitoring and centralized logging

## Data Flow

```
User Input (Voice/Text/Gesture)
        ↓
    Frontend (React)
        ↓ (HTTP/WebSocket)
    Nginx Reverse Proxy
        ↓
    FastAPI Backend
        ↓
    Agent Manager (routes to appropriate agent)
        ↓
    ┌─────────────────────────────┐
    │  Explainer | Analyzer |     │
    │  Thinker | Research |       │
    │  Helper (Coordinator)       │
    └─────────────────────────────┘
        ↓
    Ollama (Local LLM)
        ↓
    Response → Frontend → User
```

## Database Schema

11 tables across Phases 3-5:

| Table | Phase | Purpose |
|-------|-------|---------|
| `agent_conversations` | 3 | Chat history |
| `research_papers` | 3 | Paper cache |
| `agent_metrics` | 3 | Performance tracking |
| `simulations` | 4 | Experiment configs |
| `simulation_particles` | 4 | Particle data |
| `simulation_results` | 4 | Trajectory results |
| `simulation_reactions` | 4 | Reaction data |
| `collaborations` | 5 | Collaboration sessions |
| `collaboration_members` | 5 | Member roles |
| `comments` | 5 | Annotations |
| `experiment_versions` | 5 | Version history |

## Security Architecture

- JWT authentication (HS256, 24h expiry)
- Rate limiting per IP (slowapi)
- TLS 1.2/1.3 termination at Nginx
- Security headers (HSTS, CSP, XSS protection)
- Non-root Docker containers
- Kubernetes secrets for sensitive config
