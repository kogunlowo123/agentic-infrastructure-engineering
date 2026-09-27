"""Drift detection routes."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status

from ...schemas.drift import DriftDetectionRequest, DriftItem, DriftReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drift", tags=["Drift"])

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://agent-runtime:8081")


async def get_agent_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=AGENT_RUNTIME_URL, timeout=120.0) as client:
        yield client


@router.post(
    "/detect",
    response_model=DriftReport,
    status_code=status.HTTP_200_OK,
    summary="Detect infrastructure drift",
    description=(
        "Runs the drift-detector agent to compare Terraform plan output with "
        "current infrastructure state. Returns a drift report with severity assessment."
    ),
)
async def detect_drift(
    request: DriftDetectionRequest,
    client: httpx.AsyncClient = Depends(get_agent_client),
    x_tenant_id: str = Header(default="default"),
) -> DriftReport:
    """Detect infrastructure drift for specified resources."""
    session_id = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "task_type": "drift_detection",
        "session_id": session_id,
        "tenant_id": x_tenant_id,
        "input": {
            "resource_ids": request.resource_ids,
            "project_id": request.project_id,
            "terraform_plan_json": request.terraform_plan_json,
            "current_state": {},
            "drift_report": {},
            "drifted_resources": [],
            "severity": "none",
            "session_id": session_id,
            "error": None,
        },
    }

    try:
        response = await client.post("/run", json=payload)
        response.raise_for_status()
        result_data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent runtime error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent runtime service unavailable",
        ) from exc

    agent_state = result_data.get("state", {})
    drift_data = agent_state.get("drift_report", {})

    drift_items = [
        DriftItem(
            resource_id=item.get("resource_id", ""),
            attribute=item.get("attribute", ""),
            expected=item.get("expected"),
            actual=item.get("actual"),
            severity=item.get("severity", "low"),
        )
        for item in drift_data.get("items", [])
    ]

    return DriftReport(
        total_drifted=drift_data.get("total_drifted", 0),
        items=drift_items,
        severity=agent_state.get("severity", "none"),
        detected_at=datetime.now(tz=timezone.utc),
        session_id=session_id,
        recommendations=drift_data.get("recommendations", []),
    )
