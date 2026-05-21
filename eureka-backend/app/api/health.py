"""
Health check endpoints for EUREKA backend.
Provides basic, detailed, and Kubernetes readiness checks.
"""

import os
import logging
from fastapi import APIRouter
from sqlalchemy import text

from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check - checks database, Redis, and Ollama."""
    checks = {}

    # Database check
    try:
        if db.is_connected and db.engine:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        else:
            checks["database"] = "disconnected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"

    # Redis check
    try:
        import redis as redis_lib
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis_lib.from_url(redis_url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = "unhealthy"

    # Ollama check
    try:
        import httpx
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_host}/api/tags")
            if resp.status_code == 200:
                checks["ollama"] = "healthy"
            else:
                checks["ollama"] = "unhealthy"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        checks["ollama"] = "unhealthy"

    # Overall status
    all_healthy = all(v == "healthy" for v in checks.values())
    status = "healthy" if all_healthy else "degraded"

    return {"status": status, "checks": checks}


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks if the service can handle requests."""
    try:
        if db.is_connected and db.engine:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"ready": True}
        else:
            return {"ready": False}
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        return {"ready": False}
