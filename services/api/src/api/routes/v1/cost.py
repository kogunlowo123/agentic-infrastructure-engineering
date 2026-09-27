"""Cost forecasting routes."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ...schemas.cost import CostForecastRequest, CostForecastResult, CostRecommendation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cost", tags=["Cost"])

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://agent-runtime:8081")


async def get_agent_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=AGENT_RUNTIME_URL, timeout=60.0) as client:
        yield client


@router.get(
    "/forecast",
    response_model=CostForecastResult,
    summary="Get cost forecast and optimization recommendations",
    description=(
        "Runs the cost-optimizer agent to analyze spending patterns, "
        "forecast costs, and return optimization recommendations."
    ),
)
async def get_cost_forecast(
    project_id: str = Query(..., description="GCP project ID"),
    analysis_period_days: int = Query(default=30, ge=1, le=365),
    include_recommendations: bool = Query(default=True),
    client: httpx.AsyncClient = Depends(get_agent_client),
    x_tenant_id: str = Header(default="default"),
) -> CostForecastResult:
    """Get cost forecast and recommendations for a GCP project."""
    session_id = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "task_type": "cost_optimization",
        "session_id": session_id,
        "tenant_id": x_tenant_id,
        "input": {
            "project_id": project_id,
            "analysis_period_days": analysis_period_days,
            "include_recommendations": include_recommendations,
            "cost_data": {},
            "recommendations": [],
            "estimated_savings_usd": 0.0,
            "current_monthly_usd": 0.0,
            "projected_monthly_usd": 0.0,
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
    current = float(agent_state.get("current_monthly_usd", 0.0))
    projected = float(agent_state.get("projected_monthly_usd", current))
    delta = projected - current
    delta_pct = (delta / current * 100) if current > 0 else 0.0

    recs = [
        CostRecommendation(
            resource_id=r.get("resource_id", ""),
            current_cost_usd=float(r.get("current_cost_usd", 0.0)),
            recommended_action=r.get("recommended_action", ""),
            estimated_savings_usd=float(r.get("estimated_savings_usd", 0.0)),
            priority=r.get("priority", "medium"),
        )
        for r in agent_state.get("recommendations", [])
    ]

    return CostForecastResult(
        current_monthly_usd=current,
        projected_monthly_usd=projected,
        delta_usd=delta,
        delta_percent=delta_pct,
        recommendations=recs,
        total_estimated_savings_usd=float(agent_state.get("estimated_savings_usd", 0.0)),
        session_id=session_id,
        analysis_period_days=analysis_period_days,
    )
