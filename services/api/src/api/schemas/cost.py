"""Pydantic schemas for cost forecasting API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CostForecastRequest(BaseModel):
    """Query parameters for cost forecast endpoint."""

    project_id: str = Field(..., description="GCP project ID")
    analysis_period_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to analyze",
    )
    include_recommendations: bool = Field(
        default=True,
        description="Whether to include optimization recommendations",
    )


class CostRecommendation(BaseModel):
    """A single cost optimization recommendation."""

    resource_id: str
    current_cost_usd: float
    recommended_action: str
    estimated_savings_usd: float
    priority: str = "medium"


class CostForecastResult(BaseModel):
    """Result of cost forecast analysis."""

    current_monthly_usd: float
    projected_monthly_usd: float
    delta_usd: float
    delta_percent: float
    recommendations: list[CostRecommendation] = Field(default_factory=list)
    total_estimated_savings_usd: float = 0.0
    session_id: str
    analysis_period_days: int
