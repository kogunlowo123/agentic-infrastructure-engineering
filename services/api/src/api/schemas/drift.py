"""Pydantic schemas for drift detection API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DriftDetectionRequest(BaseModel):
    """Request body for drift detection endpoint."""

    resource_ids: list[str] = Field(
        default_factory=list,
        description="Specific resource IDs to check for drift",
    )
    terraform_plan_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Output of `terraform show -json` for the plan",
    )
    project_id: str = Field(..., description="GCP project ID to check")


class DriftItem(BaseModel):
    """A single infrastructure drift item."""

    resource_id: str
    attribute: str
    expected: Any = None
    actual: Any = None
    severity: Literal["critical", "high", "medium", "low"] = "low"


class DriftReport(BaseModel):
    """Result of a drift detection run."""

    total_drifted: int
    items: list[DriftItem] = Field(default_factory=list)
    severity: Literal["none", "low", "medium", "high", "critical"] = "none"
    detected_at: datetime
    session_id: str
    recommendations: list[str] = Field(default_factory=list)
