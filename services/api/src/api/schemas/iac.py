"""Pydantic schemas for IaC generation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class IaCGenerationRequest(BaseModel):
    """Request body for IaC generation endpoint."""

    resource_type: str = Field(
        ...,
        description="Terraform resource type (e.g., google_storage_bucket)",
        examples=["google_storage_bucket"],
    )
    cloud: str = Field(default="gcp", description="Cloud provider")
    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev", description="Target environment"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Resource-specific configuration",
    )
    project_id: str = Field(..., description="GCP project ID")
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Optional idempotency key to prevent duplicate operations",
    )


class SecurityFinding(BaseModel):
    """A single security finding from checkov scan."""

    check_id: str
    severity: str
    resource: str
    message: str = ""
    check_name: str = ""


class SecurityScanResult(BaseModel):
    """Result of a security scan on generated IaC."""

    passed: bool
    findings: list[SecurityFinding] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)


class IaCGenerationResult(BaseModel):
    """Response from IaC generation endpoint."""

    pr_url: Optional[str] = None
    hcl_preview: str
    security_scan_result: SecurityScanResult
    session_id: str
    pr_ready: bool = False
    approval_status: str = "pending"


class IaCPRStatus(BaseModel):
    """Status of an IaC pull request."""

    pr_id: str
    status: Literal["open", "merged", "closed", "pending_approval"]
    pr_url: Optional[str] = None
    approval_status: str
    created_at: datetime
    session_id: str
