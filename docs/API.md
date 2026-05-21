# EUREKA API Reference

## Base URL
- **Local**: `http://localhost:8000`
- **Production**: `https://eureka.example.com`

## Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/detailed` | Detailed check (DB, Redis, Ollama) |
| `GET` | `/health/ready` | Kubernetes readiness probe |

## Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send query to multi-agent system |
| `POST` | `/api/agent/{agent_type}` | Query specific agent |
| `GET` | `/api/agents/status` | Get all agent statuses |
| `WS` | `/ws/chat` | Real-time chat WebSocket |

## Simulation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/simulations/create` | Create new simulation |
| `POST` | `/api/simulations/{id}/particles` | Add particles |
| `POST` | `/api/simulations/{id}/reactions` | Add reactions |
| `POST` | `/api/simulations/{id}/run` | Run simulation |
| `GET` | `/api/simulations/{id}/results` | Get results |
| `WS` | `/ws/simulation/{id}` | Stream simulation frames |

## Collaboration Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/collaborations/create` | Create collaboration |
| `POST` | `/api/collaborations/{id}/add-member` | Add collaborator |
| `POST` | `/api/collaborations/{id}/comment` | Add comment |
| `GET` | `/api/collaborations/{id}` | Get collaboration state |
| `WS` | `/api/ws/collaboration/{id}` | Real-time collaboration |

## Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analytics/compare` | Compare experiments |
| `POST` | `/api/analytics/{id}/anomalies` | Detect anomalies |
| `GET` | `/api/analytics/{id}/trends` | Trend analysis |

## Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/experiments/{id}/export/json` | Export as JSON |
| `GET` | `/api/experiments/{id}/export/csv` | Export as CSV |
| `POST` | `/api/experiments/{id}/doi` | Generate DOI |

## Request/Response Examples

### Create Simulation
```json
POST /api/simulations/create
{
  "name": "Water Molecule",
  "description": "H2O molecular dynamics",
  "type": "molecular"
}
```

### Add Comment
```json
POST /api/collaborations/{id}/comment
{
  "user_id": "user_001",
  "text": "Check energy values at step 42",
  "line_number": 42
}
```

### Compare Experiments
```json
POST /api/analytics/compare
{
  "experiment_ids": ["exp_001", "exp_002", "exp_003"]
}
```

## Authentication

Protected endpoints require JWT Bearer token:
```
Authorization: Bearer <token>
```

Tokens are obtained via the security module and expire after 24 hours.

## Rate Limits
- General endpoints: 10 requests/second
- API endpoints: 100 requests/second
- WebSocket: Unlimited (connection-based)
