# EUREKA: Universal AI-Powered Virtual Research Lab

<p align="center">
  <img src="docs/assets/eureka_logo.png" alt="EUREKA Logo" width="220px" style="border-radius: 12px; margin-bottom: 20px;" />
</p>

<p align="center">
  <strong>🔬 Making scientific discovery and advanced research accessible to everyone, everywhere, for free. 🚀</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Powered%20By-Google%20Gemini%201.5%20Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini Powered" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/3D%20Graphics-Three.js-000000?style=for-the-badge&logo=three.js&logoColor=white" alt="Three.js" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/Minato95-ayu/EUREKA?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/stars/Minato95-ayu/EUREKA?style=flat-square&color=gold" alt="Stars" />
  <img src="https://img.shields.io/github/forks/Minato95-ayu/EUREKA?style=flat-square&color=lightgrey" alt="Forks" />
  <img src="https://img.shields.io/github/issues/Minato95-ayu/EUREKA?style=flat-square&color=red" alt="Issues" />
</p>

<p align="center">
  <a href="#-concept-to-creation-process">Process View</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-installation--setup">Quick Start</a> •
  <a href="#-security--compliance">Security</a> •
  <a href="#-founder--developer">Developer Profile</a>
</p>

---

## 💡 Concept to Creation Process

Below is a visualization of the interactive **EUREKA Cyber-Lab Dashboard** in action. Designed to run in high-performance dark mode, the interface integrates 3D viewports, gesture camera feeds, multi-agent AI logs, and real-time physical simulation data.

<p align="center">
  <img src="docs/assets/eureka_dashboard.png" alt="EUREKA Cyber-Lab Dashboard" width="100%" style="border-radius: 8px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.5);" />
</p>

**EUREKA** is a state-of-the-art, open-source AI-powered virtual research laboratory. It transforms traditional scientific discovery and education by combining **immersive 3D holographic visualization**, **gesture-based natural interface controls**, **real-time chemical/physical simulators**, and a **Wikipedia-backed multi-agent AI system** led by **ARIA** (AI Research and Innovation Assistant).

Whether you are modeling molecular mechanics, exploring the intricacies of a V8 engine, or mining scientific journals, EUREKA provides a seamless, JARVIS-style environment to search, visualize, simulate, and cite.

---

## ✨ Key Features

### 🤖 1. Gemini-Driven 3D Object Architect & Research
*   **Gemini 3D Engine**: Uses `gemini-1.5-flash` to architect complex, hierarchical 3D component trees from scratch based on real-time queries.
*   **Factual Grounding**: Integrated with the **Wikipedia API** via the `WebResearchService` to ingest real-world structural data, materials, dimensions, and colors prior to 3D generation.
*   **Dynamic GLTF Support**: Capable of dynamically generating procedural geometry or linking high-fidelity GLTF/GLB models using the custom React Three Fiber `GltfModelWrapper`.

### 🔬 2. Immersive 3D Viewport
*   **Recursive Scale Zoom**: Seamlessly navigate through multiple scales of an object (e.g., *System -> Component -> Sub-component -> Molecule -> Atom*).
*   **Interactive Controls**: Rendered using **Three.js** & **React Three Fiber** (`@react-three/drei` & `@react-three/fiber`) with real-time lighting, shaders, and shadows.

### 🖖 3. Natural User Interfaces (NUI)
*   **Hand Gesture Recognition**: Built-in camera feed powered by **MediaPipe Hands** to control the laboratory view using intuitive hand gestures (pinch zoom, fist reset, point selection, and swipe navigation).
*   **Voice Control (JARVIS Mode)**: Hands-free execution of commands (e.g., *"ARIA, simulate combustion"*, *"zoom into piston"*) using the **Web Speech API** for local speech recognition and synthesis.

### 🧪 4. Double-Engine Virtual Simulator
*   **3D Verlet Physics Engine**: Real-time simulation of Coulomb forces, Van der Waals interactions, and kinetic particle collisions.
*   **Chemical Intelligence**: Driven by **RDKit** to evaluate molecular attributes, chemical structures, and estimate reaction pathways.

### 📦 5. Autonomous Research Automation
*   An independent automation layer (`eureka-automation`) running on **Node.js, TypeScript, and BullMQ** to crawl, extract, and index academic publications from **ArXiv** and **PubMed**.

---

## 🏗️ Architecture

```
                                  ┌─────────────────────────────┐
                                  │      EUREKA Frontend        │
                                  │   (React 19 + Vite + TS)    │
                                  └──────────────┬──────────────┘
                                                 │
                                     WebSocket / HTTP Requests
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │       EUREKA Backend        │
                                  │     (FastAPI + Python)      │
                                  └──────────────┬──────────────┘
                                                 │
                ┌────────────────────────────────┼────────────────────────────────┐
                ▼                                ▼                                ▼
   ┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
   │     AI Agent Mesh       │      │   Simulation Engines    │      │    Knowledge Services   │
   │ - Explainer             │      │ - Verlet Physics (3D)   │      │ - Wikipedia REST API    │
   │ - Analyzer              │      │ - RDKit Chemistry       │      │ - Google Gemini API     │
   │ - Thinker               │      └─────────────────────────┘      │ - Local Ollama Fallback │
   │ - Helper (Coordinator)  │                                       └─────────────────────────┘
   └─────────────────────────┘
```

---

## 📂 Project Structure

```bash
EUREKA/
├── eureka-backend/             # FastAPI backend application
│   ├── app/
│   │   ├── agents/             # AI Multi-Agent system (Helper, Explainer, etc.)
│   │   ├── api/                # API Endpoints (Objects, Auth, WebSockets)
│   │   ├── services/           # Gemini 3D Engine, Web Research, Chemistry, Physics
│   │   └── data/               # Procedural templates & demo objects (e.g., car_engine.json)
│   ├── tests/                  # Pytest unit and integration tests
│   └── main.py                 # Backend application entrypoint
│
├── eureka-frontend/            # React + TypeScript + Three.js client
│   ├── src/
│   │   ├── components/         # 3D Viewport, GltfWrapper, UI Controls, Camera Stream
│   │   ├── pages/              # Cyber-lab dashboards and settings panels
│   │   └── App.tsx             # Main dashboard shell & gesture mapping loops
│   └── package.json
│
├── eureka-automation/          # TypeScript background worker & crawler
│   ├── src/
│   │   ├── scrapers/           # Academic crawling engines (ArXiv, PubMed)
│   │   └── queue/              # BullMQ message queue setup
│   └── package.json
│
├── kubernetes/                 # K8s manifests for production deployment
├── helm/                       # Helm packaging for scalable cloud rollouts
├── monitoring/                 # Prometheus metrics and Grafana alerts
└── docker-compose.yml          # Consolidated multi-container setup (Backend, Frontend, Redis, DB, Ollama)
```

---

## 🚀 Installation & Setup

### Option 1: Quickstart with Docker Compose (Recommended)

To run the complete suite, including database, caching, local models, and analytics dashboards:

```bash
# Clone the repository
git clone https://github.com/Minato95-ayu/EUREKA.git
cd EUREKA

# Configure environment variables
cp .env.example .env # Add your GEMINI_API_KEY here

# Build and start services
docker-compose up --build -d

# Pull the default local model for Ollama (optional fallback)
docker-compose exec ollama ollama pull llama3
```

Access the platform:
*   **Frontend Web Interface**: [http://localhost:3000](http://localhost:3000)
*   **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Local Ollama Server**: [http://localhost:11434](http://localhost:11434)

---

### Option 2: Local Manual Setup (Development Mode)

#### 1. Backend Setup (FastAPI)
```bash
cd eureka-backend
python -m venv venv

# Activate Virtual Environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install requirements (ensure RDKit-supported python version)
pip install -r requirements.txt

# Export your keys
export GEMINI_API_KEY="your_api_key_here"  # Windows PowerShell: $env:GEMINI_API_KEY="your_api_key_here"

# Start the application
python main.py
```

#### 2. Frontend Setup (React)
```bash
cd ../eureka-frontend
npm install
npm run dev
```

---

## 🛡️ Security & Compliance

EUREKA is designed with robust security protocols suited for scientific and educational sandbox environments:

*   **API Security**: Implements granular CORS origin controls, custom secure headers (HSTS, CSP, X-Frame-Options), and client rate-limiting via the `slowapi` middleware.
*   **Authentication**: Secure token-based user authentication using **JSON Web Tokens (JWT)** with HS256 encryption.
*   **Access Isolation**: Non-root container privileges configured inside both the frontend and backend Dockerfiles.
*   **Resource Throttling**: Sandboxed environments prevent heavy model generation or simulation operations from overflowing backend compute cycles.

---

## 🧪 Testing Suite

EUREKA maintains a rigorous test suite validating the physics simulator, agent coordination, and chemistry calculations.

```bash
# Navigate to the backend directory
cd eureka-backend

# Run complete pytest suite with coverage metrics
pytest -v --cov=app
```

---

## 📈 Roadmap

*   [x] **Phase 1**: Cyber-lab 3D dashboard & Three.js canvas integration.
*   [x] **Phase 2**: MediaPipe hand gestures & Web Speech voice control MVP.
*   [x] **Phase 3**: Wikipedia-grounded Gemini 3D Object generation.
*   [x] **Phase 4**: Verlet 3D physics simulator and RDKit-driven chemistry solver.
*   [ ] **Phase 5**: Full AR/VR support utilizing WebXR devices.
*   [ ] **Phase 6**: Custom visual physics simulator node editor.
*   [ ] **Phase 7**: Real-time collaborative shared virtual lab sessions via Redis-backed WebSockets.

---

## 👑 Founder & Developer

<table border="0" cellpadding="10" cellspacing="0">
  <tr>
    <td valign="top" width="180">
      <img src="docs/assets/ayush_kaushik.jpg" alt="Ayush Kaushik" width="160" style="border-radius: 12px; border: 3px solid #009688; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
    </td>
    <td valign="top">
      <h3>Ayush Kaushik</h3>
      <p><strong>Lead Architect & Creator of EUREKA</strong></p>
      <ul>
        <li>💻 <strong>Role:</strong> Full-Stack AI Engineer & System Designer</li>
        <li>🎓 <strong>Status:</strong> Student Developer pushing boundaries in Virtual Scientific Simulation</li>
        <li>🌐 <strong>GitHub:</strong> <a href="https://github.com/Minato95-ayu">@Minato95-ayu</a></li>
        <li>✉️ <strong>Email:</strong> <a href="mailto:ayushkaushik1441@gmail.com">ayushkaushik1441@gmail.com</a></li>
      </ul>
      <p><em>"EUREKA was built to democratize access to advanced scientific research interfaces. By combining spatial computing, voice controls, and LLM-driven generation, we enable students and researchers to visualize and experiment with complex structures without expensive laboratory setups."</em></p>
    </td>
  </tr>
</table>

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

## 📝 Citation

If you use EUREKA in your academic research, please cite our repository:

```bibtex
@software{eureka2026,
  title={EUREKA: Universal AI-Powered Virtual Research Lab},
  author={Kaushik, Ayush},
  year={2026},
  url={https://github.com/Minato95-ayu/EUREKA}
}
```

<p align="center">
  Made with ❤️ for scientific education and global research. <br/>
  <strong>EUREKA — Where Discovery Begins. 🔬🚀</strong>
</p>
