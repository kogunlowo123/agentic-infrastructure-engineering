"""State definitions for LangGraph agent workflows."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class IaCGenerationState(TypedDict):
    """State for the IaC generator LangGraph workflow."""

    # Input
    requirements: dict  # cloud, resource_type, config, environment, project_id

    # Retrieved context
    retrieved_templates: list[dict]

    # Generation outputs
    generated_hcl: str

    # Security scan results
    security_scan: dict  # findings: list, passed: bool, severity_counts: dict

    # PR tracking
    pr_url: Optional[str]
    pr_number: Optional[int]
    branch_name: Optional[str]

    # Approval gate
    approval_status: Literal["pending", "approved", "rejected"]

    # Error handling
    error: Optional[str]
    retry_count: int

    # Tracing
    session_id: str
    trace_id: str
    tenant_id: str


class DriftDetectionState(TypedDict):
    """State for the drift detector LangGraph workflow."""

    # Input
    resource_ids: list[str]
    project_id: str
    terraform_plan_json: dict
    current_state: dict

    # Output
    drift_report: dict  # total_drifted, items, severity
    drifted_resources: list[dict]

    # Severity assessment
    severity: Literal["none", "low", "medium", "high", "critical"]

    # Metadata
    session_id: str
    error: Optional[str]


class CostOptimizationState(TypedDict):
    """State for the cost optimizer LangGraph workflow."""

    # Input
    analysis_period_days: int
    project_id: str
    include_recommendations: bool

    # Analysis data
    cost_data: dict  # raw cost breakdown by service and time

    # Output
    recommendations: list[dict]
    estimated_savings_usd: float
    current_monthly_usd: float
    projected_monthly_usd: float

    # Metadata
    session_id: str
    error: Optional[str]
