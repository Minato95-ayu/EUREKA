# EUREKA Production Hardening Guide

This file is the production-readiness source of truth for anyone continuing or rebuilding EUREKA.

## Current Priority

Treat the app as an MVP until these gates are complete:

1. Every API and WebSocket must pass authentication and RBAC checks in production.
2. Every expensive path must have limits: request size, upload count/size, AI prompt length, AI concurrency/rate, simulation steps, particles, and export size.
3. Runtime state must not live only in process memory when more than one backend replica runs.
4. Docker, CI, Nginx, Kubernetes, and frontend API configuration must agree on paths and environment variable names.
5. Lint, tests, dependency audit, and image build must be CI gates.
6. Security headers, metrics, structured logs, and real migrations must exist before public deployment.

## Production Environment Defaults

Required environment variables:

- `ENVIRONMENT=production`
- `AUTH_REQUIRED=true`
- `SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=postgresql://...`
- `REDIS_URL=redis://...`
- `OLLAMA_HOST=http://ollama:11434`
- `GEMINI_API_KEY=<optional-provider-key>`
- `VITE_API_URL=/`

Do not use these in production:

- `SECRET_KEY=your-secret-key-change-in-production`
- `latest` image tags
- host-exposed Postgres/Redis/Ollama ports
- browser-side hardcoded `localhost`

## Auth/RBAC Model

Use JWT Bearer tokens. The token payload should include:

```json
{
  "user_id": "user-123",
  "role": "viewer|editor|admin",
  "exp": 1234567890
}
```

Role permissions:

- `viewer`: read-only endpoints and WebSocket subscribe
- `editor`: create simulations, comments, object generation, agent requests
- `admin`: collaboration membership, exports, operational endpoints

In development, `AUTH_REQUIRED=false` may be used for fast local testing. In production, startup must fail if auth is disabled.

## State Model

Current code still contains in-memory fallback state. Production target:

- Simulations: persisted in Postgres; active frame/state cache in Redis with TTL.
- Agent response cache: Redis with TTL and per-user keying.
- Collaboration rooms: Redis pub/sub or Socket.IO adapter, not process-local sets.
- WebSocket authorization: token checked before `accept()`.

## Rate and Size Limits

Recommended production defaults:

- Request body: 2 MB global default.
- Image upload: max 4 files, max 5 MB each, only JPEG/PNG/WebP.
- AI prompt: max 4,000 characters.
- AI request rate: 20/min/user, 60/min/IP.
- Object generation: 10/min/user.
- Simulation: max 5,000 steps, max 250 particles, `0 < time_step <= 0.05`.
- WebSocket rooms: max 5,000 concurrent connections per deployment, per-user room cap.

## CI Gates

Required checks:

```bash
cd eureka-backend && python -m pytest
cd eureka-frontend && npm run lint && npm run build && npm audit --audit-level=moderate
docker build -t eureka-backend ./eureka-backend
docker build -t eureka-frontend ./eureka-frontend
```

## Migration Policy

Move startup SQL from `app/database.py` into Alembic migrations. App containers should never mutate schema during normal request-serving startup.

## Observability Policy

Expose:

- `GET /metrics` for Prometheus.
- Structured JSON logs in production.
- Request IDs.
- Latency, status code, auth failures, AI calls, simulation runtime, WebSocket connects/disconnects.

## Current Implementation Status

This hardening pass adds production scaffolding and fixes critical wiring issues. Remaining high-effort items are Redis-backed WebSocket fanout, Alembic migration conversion, and full RBAC resource ownership checks.
