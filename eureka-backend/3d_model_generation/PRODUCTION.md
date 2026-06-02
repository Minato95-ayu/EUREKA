# Production Checklist

This module is designed to run as a separate service first. That keeps the main
Eureka backend safe while the 3D pipeline matures.

## Required Environment

```text
EUREKA_3D_PORT=8093
EUREKA_3D_OUTPUT_ROOT=/app/generated
EUREKA_3D_API_KEY=<strong-secret>
EUREKA_3D_MAX_QUERY_LENGTH=160
```

If `EUREKA_3D_API_KEY` is set, protected endpoints require:

```text
x-api-key: <strong-secret>
```

## Production Endpoints

```text
GET  /health
GET  /ready
POST /api/3d/generate
POST /api/3d/jobs
GET  /api/3d/jobs/{jobId}
GET  /api/3d/blueprints/{objectId}
GET  /api/3d/models/{objectId}.glb
GET  /api/3d/mesh-upgrades/{objectId}
POST /api/3d/mesh-upgrades/{objectId}/apply
```

Use `/api/3d/jobs` for UI flows and heavier future generation. The current
worker runs in FastAPI background tasks; replace it with Redis/Celery/RQ when
generation becomes slow or distributed.

## Docker

```bash
docker compose up --build
```

## Validation

After generating an object, validate the saved files:

```bash
python validate_output.py generated/blueprints/{objectId}.json generated/models/{objectId}.glb
```

## What Is Production-Hardened Here

- explicit config through environment variables,
- optional API key protection,
- health and readiness endpoints,
- structured request logging,
- job status files,
- Dockerfile and service compose file,
- GLB header validation utility,
- high-quality mesh replacement contract.

## Next Scale Step

For large usage, replace file job storage with a database and object storage:

```text
jobs: PostgreSQL / Redis
models: S3-compatible object storage
workers: Celery / RQ / cloud queue
metrics: Prometheus / OpenTelemetry
```

