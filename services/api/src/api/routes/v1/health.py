"""Health and readiness check endpoints."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe — returns 200 if the service is running."""
    return {"status": "ok", "version": "0.1.0", "service": "agentic-infrastructure-api"}


@router.get("/readiness")
async def readiness() -> dict[str, Any]:
    """Readiness probe — checks database and agent-runtime connectivity."""
    checks: dict[str, str] = {}

    # Check database
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        try:
            import psycopg2

            conn = psycopg2.connect(database_url, connect_timeout=3)
            conn.close()
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
    else:
        checks["database"] = "not configured"

    # Check agent-runtime
    agent_runtime_url = os.getenv("AGENT_RUNTIME_URL", "http://agent-runtime:8081")
    try:
        import httpx

        response = httpx.get(f"{agent_runtime_url}/health", timeout=3.0)
        checks["agent_runtime"] = "ok" if response.status_code == 200 else f"status: {response.status_code}"
    except Exception as exc:
        checks["agent_runtime"] = f"error: {exc}"

    all_ok = all(v == "ok" or v == "not configured" for v in checks.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "version": "0.1.0",
    }
