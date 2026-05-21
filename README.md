# EUREKA: The Universal AI-Powered Virtual Research Lab

<p align="center">
  <strong>🔬 Making scientific discovery accessible to everyone, everywhere, for free. 🚀</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-documentation">Docs</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

EUREKA is a revolutionary, open-source platform that transforms scientific education and research through immersive 3D visualization, gesture-based control, and intelligent AI-powered analysis. Built entirely with free and open-source technologies, EUREKA democratizes access to advanced scientific tools for students, researchers, and educators worldwide.

## Current Product Direction

EUREKA is being refocused into a JARVIS-style AI-powered 3D experimental lab with ARIA, the AI Research and Innovation Assistant. The immediate goal is to build a complete interaction loop:

```text
Search -> visualize -> select -> ask ARIA -> simulate -> explain -> cite
```

See [docs/JARVIS_VISION.md](docs/JARVIS_VISION.md) for the detailed vision and [PROJECT_STATUS.md](PROJECT_STATUS.md) for the honest current implementation status.

EUREKA also now includes an early automation layer in [eureka-automation/](eureka-automation/) for research scraping, batch experiment orchestration, and ARIA-assisted analysis. See [docs/AUTOMATION_LAYER.md](docs/AUTOMATION_LAYER.md).

## ✨ Key Features

### 🔬 3D Holographic Visualization
- Interactive 3D models viewable from any angle
- Recursive zoom: Explore from atoms → molecules → objects
- Real-time rendering with Three.js and React Three Fiber
- Hand gesture-based navigation (MediaPipe)
- Voice command support

### 🤖 Multi-Agent AI System
Five specialized AI agents working together:
| Agent | Role |
|-------|------|
| **Explainer** | Simplifies complex scientific concepts |
| **Analyzer** | Calculates properties and characteristics |
| **Thinker** | Predicts outcomes and consequences |
| **Research Integrator** | Fetches relevant research papers |
| **Helper** | Master coordinator orchestrating all agents |

### 🧪 Virtual Simulation Engine
- **Physics**: Coulomb forces, Van der Waals interactions, Verlet integration
- **Chemistry**: Molecular structure analysis (RDKit), reaction simulation
- **Real-time**: Watch particles interact live with energy tracking
- **Trajectory**: Record and replay particle movement history

### 📚 Research Integration
- ArXiv API integration for physics/math papers
- PubMed API integration for medical/biology papers
- Semantic search for finding related research
- Citation management and knowledge graphs

### 🤝 Collaboration Features
- Multi-user experiments in shared virtual labs
- Real-time synchronization via WebSocket
- Role-based access control (Owner, Editor, Viewer)
- Comments, annotations, and experiment versioning

### 📊 Advanced Analytics
- Experiment comparison with t-test/ANOVA statistical analysis
- Z-score anomaly detection in results
- Linear regression trend analysis
- Export in multiple formats (JSON, CSV, PDF)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EUREKA Platform                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Frontend (React + Three.js)             │   │
│  │  - 3D Visualization    - Gesture Recognition      │   │
│  │  - Voice Control       - Real-time Chat           │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Backend (FastAPI + Python)                │   │
│  │  - Multi-Agent AI System  - Simulation Engine     │   │
│  │  - Research Integration   - WebSocket Server      │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Services & Infrastructure               │   │
│  │  - Ollama (Llama 3)   - PostgreSQL                │   │
│  │  - Redis              - RDKit                     │   │
│  │  - ArXiv/PubMed APIs  - Prometheus/ELK            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- Or: Python 3.11+, Node.js 22+, PostgreSQL 15+

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/Minato95-ayu/EUREKA.git
cd EUREKA

# Start all services
docker-compose up -d

# Pull Ollama model
docker-compose exec ollama ollama pull llama3

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Ollama: http://localhost:11434
```

### Option 2: Local Development

```bash
# Backend setup
cd eureka-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Frontend setup (new terminal)
cd eureka-frontend
npm install
npm run dev

# Ollama setup (new terminal)
ollama pull llama3
ollama serve
```

## 📁 Project Structure

```
eureka/
├── eureka-backend/             # FastAPI backend
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   ├── agents/             # AI agents
│   │   ├── services/           # Business logic
│   │   ├── websocket/          # WebSocket handlers
│   │   ├── security.py         # JWT & rate limiting
│   │   ├── database.py         # DB connection & migrations
│   │   └── config.py           # Settings
│   ├── tests/                  # Backend tests
│   ├── requirements.txt        # Python dependencies
│   ├── main.py                 # Entry point
│   └── Dockerfile              # Container image
│
├── eureka-frontend/            # React frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   └── services/           # API services
│   ├── package.json            # Node dependencies
│   ├── vite.config.ts          # Vite configuration
│   └── Dockerfile              # Container image
│
├── kubernetes/                 # K8s manifests
├── helm/                       # Helm chart
├── monitoring/                 # Prometheus & alerts
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
│
├── docker-compose.yml          # Docker Compose
├── docker-compose-elk.yml      # ELK Stack
├── nginx.conf                  # Nginx reverse proxy
├── init.sql                    # Database initialization
├── .github/workflows/          # CI/CD pipeline
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## 🔧 Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Three.js, React Three Fiber, MediaPipe, TailwindCSS |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy, Pydantic, Socket.io, Ollama, RDKit |
| **Database** | PostgreSQL 15, Redis 7, pgvector |
| **DevOps** | Docker, Kubernetes, Helm, GitHub Actions, Nginx |
| **Monitoring** | Prometheus, ELK Stack (Elasticsearch, Logstash, Kibana) |
| **Security** | JWT (PyJWT), slowapi rate limiting, TLS 1.2/1.3, CORS |

## 🔐 Security

- **JWT Authentication** — Token-based user authentication (HS256, 24h expiry)
- **Rate Limiting** — DDoS protection via slowapi
- **SSL/TLS** — HTTPS with TLS 1.2/1.3 via Nginx
- **Security Headers** — HSTS, X-Content-Type-Options, X-Frame-Options, XSS-Protection
- **Input Validation** — Pydantic models for all API inputs
- **CORS** — Configurable cross-origin security
- **Non-root Containers** — Docker images run as unprivileged user

## 📊 Monitoring & Observability

- **Prometheus** — Metrics collection with alert rules
- **ELK Stack** — Centralized logging
- **Health Checks** — `/health`, `/health/detailed`, `/health/ready`
- **Alerts** — HighErrorRate, HighLatency, PodCrashLooping, DBConnectionPool

## 🧪 Running Tests

```bash
# Backend tests
cd eureka-backend
pytest tests/ -v --cov=app

# Full test suite (23 tests)
pytest -v
```

## 📈 Roadmap

### Current Version (v1.0) ✅
- 3D visualization with gesture control
- Multi-agent AI system (5 agents)
- Physics and chemistry simulation engine
- Research paper integration (ArXiv + PubMed)
- Real-time collaboration features
- Production deployment infrastructure

### Planned (v1.1+)
- 🔄 AR/VR support (WebXR)
- 🔄 Advanced molecular visualization
- 🔄 Mobile app (iOS/Android)
- 🔄 Offline mode
- 🔄 Custom simulation builder

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

```bash
# Fork → Clone → Branch → Commit → Push → PR
git checkout -b feature/amazing-feature
git commit -m 'Add amazing feature'
git push origin feature/amazing-feature
```

## 📄 License

EUREKA is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

## 📝 Citation

```bibtex
@software{eureka2024,
  title={EUREKA: Universal AI-Powered Virtual Research Lab},
  author={Kaushik, Ayush},
  year={2024},
  url={https://github.com/Minato95-ayu/EUREKA}
}
```

## 🙏 Acknowledgments

Built with: [Three.js](https://threejs.org/) • [React](https://react.dev/) • [FastAPI](https://fastapi.tiangolo.com/) • [Ollama](https://ollama.ai/) • [RDKit](https://www.rdkit.org/) • [MediaPipe](https://mediapipe.dev/)

---

<p align="center">
  Made with ❤️ for science education and research<br>
  <strong>EUREKA — Where Discovery Happens 🔬🚀</strong>
</p>
