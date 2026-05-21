# Contributing to EUREKA

Thank you for your interest in contributing to EUREKA! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EUREKA.git
   cd EUREKA
   ```
3. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/amazing-feature
   ```

## 💻 Development Setup

### Backend
```bash
cd eureka-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-asyncio  # Dev dependencies
python main.py
```

### Frontend
```bash
cd eureka-frontend
npm install
npm run dev
```

### Docker (Full Stack)
```bash
docker-compose up -d
```

## 📋 Guidelines

### Code Style
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Follow ESLint configuration
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`)

### Pull Requests
1. Update documentation for any API changes
2. Add tests for new features
3. Ensure all tests pass: `pytest tests/ -v`
4. Keep PRs focused — one feature per PR

### Testing
```bash
# Run all backend tests
cd eureka-backend
pytest tests/ -v --cov=app

# Run specific test file
pytest tests/test_phase5.py -v
```

## 🐛 Reporting Issues

- Use GitHub Issues
- Include: steps to reproduce, expected vs actual behavior, environment details
- Label appropriately: `bug`, `feature`, `documentation`

## 📁 Project Structure

| Directory | Description |
|-----------|-------------|
| `eureka-backend/app/agents/` | AI agent implementations |
| `eureka-backend/app/services/` | Business logic services |
| `eureka-backend/app/api/` | FastAPI route handlers |
| `eureka-backend/tests/` | Backend test suite |
| `eureka-frontend/src/` | React frontend source |
| `kubernetes/` | K8s deployment manifests |
| `monitoring/` | Prometheus & alert configs |
| `docs/` | Project documentation |

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make EUREKA better! 🔬🚀
